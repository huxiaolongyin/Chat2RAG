from typing import AsyncIterator, Optional

from chat2rag.logger import get_logger
from chat2rag.services.command_service import CommandService

from .base import ResponseStrategy

logger = get_logger(__name__)


class CommandStrategy(ResponseStrategy):
    """命令匹配策略：模糊匹配用户输入，返回命令内容"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.command_service = CommandService()

    async def can_handle(self, query: str) -> bool:
        """检查是否能匹配到命令"""
        command = await self._match_command(query)
        return command is not None

    async def execute(self, query: str) -> AsyncIterator[str]:
        """执行命令匹配并返回命令内容"""
        command = await self._match_command(query)

        if command:
            logger.info(f"Command matched: {command.name} (code: {command.code})")
            reply = command.reply if command.reply else "."
            async for item in self._yield_stream(reply, "Command answer", command=command.code):
                yield item

    async def _match_command(self, query: str) -> Optional[object]:
        """
        模糊匹配命令
        匹配逻辑：
        1. 先匹配启用的命令
        2. 按优先级排序
        3. 检查命令名称、代码或变体是否包含用户输入
        """
        try:
            if not query:
                return None

            # 只查询启用的命令
            commands = (
                await self.command_service.model.filter(is_active=True)
                .prefetch_related("variants")
                .order_by("-priority", "-id")
                .all()
            )

            query_lower = query.lower().strip()

            for command in commands:
                # 匹配命令名称
                if query_lower in command.name.lower():
                    return command

                # 匹配命令代码
                if query_lower in command.code.lower():
                    return command

                # 匹配变体文本
                variants = await command.variants.all()
                for variant in variants:
                    if variant.text.lower() in query_lower:
                        return command

            return None

        except Exception as e:
            logger.error(f"Error matching command: {str(e)}")
            return None
