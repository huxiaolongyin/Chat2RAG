from typing import AsyncIterator

from chat2rag.core.flow.flow import handle_flow

from .base import ResponseStrategy


class FlowStrategy(ResponseStrategy):
    """流程处理策略"""

    async def can_handle(self, query: str) -> bool:
        return bool(self.request.flows)

    async def execute(self, query: str) -> AsyncIterator[str]:
        chunks = []
        async for chunk in handle_flow(self.request.chat_id, query):
            chunks.append(chunk)

        if chunks:
            async for item in self._yield_stream("".join(chunks), "Flow answer"):
                yield item
