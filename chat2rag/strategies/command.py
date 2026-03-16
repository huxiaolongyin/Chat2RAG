import re
from dataclasses import dataclass
from typing import AsyncIterator, Optional

from chat2rag.config import CONFIG
from chat2rag.core.logger import get_logger
from chat2rag.models.command import Command, CommandVariant, ParamType
from chat2rag.services.command_service import CommandService
from chat2rag.utils.intent_recognizer import fuzzy_match, intent_recognizer
from chat2rag.utils.param_extractor import extract_number, match_pattern

from .base import ResponseStrategy

logger = get_logger(__name__)


@dataclass
class MatchResult:
    """命令匹配结果"""

    command: object
    param_value: Optional[int | str] = None
    param_raw: Optional[str] = None


class CommandStrategy(ResponseStrategy):
    """命令匹配策略：规则优先 -> 模糊匹配 -> LLM兜底"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command_service = CommandService()
        self._cached_commands = None

    async def can_handle(self, query: str) -> bool:
        """检查是否能匹配到命令"""
        result = await self._match_command(query)
        return result is not None

    async def execute(self, query: str) -> AsyncIterator[str]:
        """执行命令匹配并返回命令内容"""
        result = await self._match_command(query)

        if result and result.command:
            command = result.command
            logger.info(f"Command matched: {command.name} (code={command.code})")

            self.handler.set_source(command.name)
            reply = command.reply if command.reply else "."

            arguments = {}
            if result.param_value is not None:
                arguments["value"] = result.param_value
                if result.param_raw:
                    arguments["raw"] = result.param_raw

            async for item in self._yield_stream(
                reply, command.name, command=command.code, arguments=arguments
            ):
                yield item

    async def _get_active_commands(self):
        """获取启用的命令列表（带缓存）"""
        if self._cached_commands is None:
            self._cached_commands = (
                await self.command_service.model.filter(is_active=True)
                .prefetch_related("variants")
                .order_by("-priority", "-id")
                .all()
            )
        return self._cached_commands

    async def _match_command(self, query: str) -> Optional[MatchResult]:
        """
        三层匹配策略：
        1. 规则匹配：精确匹配 + 模式匹配
        2. 模糊匹配：字符串相似度
        3. LLM 兜底：语义理解
        """
        try:
            if not query:
                return None

            commands = await self._get_active_commands()
            query_lower = query.lower().strip()

            # 第一层：规则匹配
            for command in commands:
                result = await self._rule_match(command, query, query_lower)
                if result:
                    logger.debug(f"Rule matched: {command.code}")
                    return result

            # 第二层：模糊匹配
            result = await self._fuzzy_match_layer(query, commands)
            if result:
                logger.debug(f"Fuzzy matched: {result.command.code}")
                return result

            # 第三层：LLM 兜底（可配置关闭）
            if getattr(CONFIG, "COMMAND_LLM_FALLBACK", True):
                result = await self._llm_match(query, commands)
                if result:
                    logger.debug(f"LLM matched: {result.command.code}")
                    return result

            return None

        except Exception as e:
            logger.exception("Failed to match command")
            return None

    async def _rule_match(
        self, command, query: str, query_lower: str
    ) -> Optional[MatchResult]:
        """规则匹配：精确匹配 + 模式匹配"""

        # 匹配命令名称
        if query_lower in command.name.lower() or command.name.lower() in query_lower:
            param = await self._extract_param(command, query)
            return MatchResult(
                command=command,
                param_value=param.get("value"),
                param_raw=param.get("raw"),
            )

        # 匹配命令代码
        if query_lower in command.code.lower() or command.code.lower() in query_lower:
            param = await self._extract_param(command, query)
            return MatchResult(
                command=command,
                param_value=param.get("value"),
                param_raw=param.get("raw"),
            )

        # 匹配变体
        variants = await command.variants.all()
        for variant in variants:
            # 模式匹配（带参数）
            if variant.pattern:
                result = match_pattern(query, variant.pattern)
                if result:
                    return MatchResult(
                        command=command,
                        param_value=result.normalized_value,
                        param_raw=result.raw_value,
                    )

            # 文本包含匹配
            variant_text = variant.text.lower()
            if variant_text in query_lower or query_lower in variant_text:
                param = await self._extract_param(command, query)
                return MatchResult(
                    command=command,
                    param_value=param.get("value"),
                    param_raw=param.get("raw"),
                )

        return None

    async def _fuzzy_match_layer(
        self, query: str, commands: list
    ) -> Optional[MatchResult]:
        """模糊匹配层：基于字符串相似度"""
        threshold = getattr(CONFIG, "COMMAND_FUZZY_THRESHOLD", 0.7)

        candidates = []
        for command in commands:
            variants = await command.variants.all()
            for variant in variants:
                candidates.append(
                    {
                        "text": variant.text,
                        "command": command,
                    }
                )

        result = fuzzy_match(query, candidates, threshold)
        if result:
            candidate, score = result
            command = candidate["command"]
            param = await self._extract_param(command, query)
            logger.info(f"Fuzzy match score: {score:.2f}")
            return MatchResult(
                command=command,
                param_value=param.get("value"),
                param_raw=param.get("raw"),
            )

        return None

    async def _llm_match(self, query: str, commands: list) -> Optional[MatchResult]:
        """LLM 兜底匹配"""
        try:
            result = await intent_recognizer.recognize(query, commands)

            if not result or not result.matched or not result.code:
                return None

            for command in commands:
                if command.code == result.code:
                    param_value = None
                    param_raw = None
                    if result.slots and "value" in result.slots:
                        param_value = result.slots["value"]
                        param_raw = str(param_value)
                    return MatchResult(
                        command=command,
                        param_value=param_value,
                        param_raw=param_raw,
                    )

            return None

        except Exception as e:
            logger.warning(f"LLM match failed: {e}")
            return None

    async def _extract_param(self, command: Command, query: str) -> dict:
        """从查询中提取参数"""
        result = {}

        if not hasattr(command, "param_type") or command.param_type == ParamType.NONE:
            return result

        if command.param_type == ParamType.NUMBER:
            number = extract_number(query)
            if number is not None:
                result["value"] = number
                result["raw"] = str(number)

        return result
