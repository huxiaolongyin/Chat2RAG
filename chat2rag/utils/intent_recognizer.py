import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Optional

from chat2rag.core.logger import get_logger
from chat2rag.utils.llm_client import LLMClient

logger = get_logger(__name__)

INTENT_PROMPT = """你是一个命令意图识别助手。根据用户输入，识别意图并提取参数。

可用命令列表：
{commands_info}

用户输入：{user_input}

请返回JSON格式（不要包含```json标记）：
{{
  "matched": true或false,
  "intent": "命令code，未匹配则为null",
  "slots": {{"value": "参数值"}},
  "confidence": 0.0到1.0的置信度
}}

注意：
- 数字参数提取为整数，如"五十"转为 {{"value": 50}}
- 如果用户输入与任何命令都不相关，返回 {{"matched": false}}"""


@dataclass
class IntentResult:
    """意图识别结果"""

    matched: bool
    code: Optional[str] = None
    slots: dict = None
    confidence: float = 0.0

    def __post_init__(self):
        if self.slots is None:
            self.slots = {}


class IntentRecognizer:
    """意图识别器：LLM 兜底匹配"""

    def __init__(self):
        self.llm_client = LLMClient()

    async def recognize(
        self, user_input: str, commands: list
    ) -> Optional[IntentResult]:
        """
        使用 LLM 识别用户意图

        Args:
            user_input: 用户输入
            commands: 可用命令列表

        Returns:
            IntentResult 或 None
        """
        try:
            commands_info = self._format_commands(commands)
            prompt = INTENT_PROMPT.format(
                commands_info=commands_info, user_input=user_input
            )

            response = await self.llm_client.acall_llm(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.0,
            )

            result = self._parse_response(response)
            return result

        except Exception as e:
            logger.exception(f"LLM intent recognition failed: {e}")
            return None

    def _format_commands(self, commands: list) -> str:
        """格式化命令列表为提示词"""
        lines = []
        for cmd in commands:
            variants = []
            for v in cmd.variants:
                variants.append(v.text)

            examples = getattr(cmd, "examples", None) or []

            info_parts = [f"- {cmd.code}: {cmd.name}"]
            if examples:
                info_parts.append(f"(示例: {', '.join(examples[:3])})")
            if variants:
                info_parts.append(f"(变体: {', '.join(variants[:3])})")

            lines.append(" ".join(info_parts))

        return "\n".join(lines)

    def _parse_response(self, response: str) -> Optional[IntentResult]:
        """解析 LLM 响应"""
        try:
            response = response.strip()

            if "```" in response:
                match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
                if match:
                    response = match.group(1).strip()

            result = json.loads(response)

            matched = result.get("matched", False)
            if not matched:
                return IntentResult(matched=False)

            confidence = result.get("confidence", 0.5)
            if confidence < 0.5:
                logger.info(f"LLM confidence too low: {confidence}, ignoring result")
                return IntentResult(matched=False)

            return IntentResult(
                matched=True,
                code=result.get("intent"),
                slots=result.get("slots", {}),
                confidence=confidence,
            )

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error parsing LLM response: {e}")
            return None


def calculate_similarity(s1: str, s2: str) -> float:
    """计算两个字符串的相似度"""
    s1 = s1.lower().strip()
    s2 = s2.lower().strip()
    return SequenceMatcher(None, s1, s2).ratio()


def fuzzy_match(
    query: str, candidates: list, threshold: float = 0.7
) -> Optional[tuple]:
    """
    模糊匹配：找到最佳匹配项

    Args:
        query: 用户输入
        candidates: 候选项列表 [{"text": "...", "command": Command}, ...]
        threshold: 相似度阈值

    Returns:
        (匹配项, 相似度) 或 None
    """
    query = query.lower().strip()
    best_match = None
    best_score = 0

    for candidate in candidates:
        text = candidate.get("text", "").lower().strip()

        if text in query or query in text:
            score = 0.9
        else:
            score = calculate_similarity(query, text)

        if score > best_score and score >= threshold:
            best_score = score
            best_match = candidate

    if best_match:
        return (best_match, best_score)
    return None


intent_recognizer = IntentRecognizer()
