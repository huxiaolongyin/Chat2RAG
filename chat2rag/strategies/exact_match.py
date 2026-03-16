from typing import AsyncIterator

from chat2rag.services.collection_service import document_service

from .base import ResponseStrategy


class ExactMatchStrategy(ResponseStrategy):
    """精确匹配策略"""

    async def can_handle(self, query: str) -> bool:
        return self.request.precision_mode == 1 and bool(self.request.collections)

    async def execute(self, query: str) -> AsyncIterator[str]:
        for collection in self.request.collections:
            document = await document_service.query_exact(
                collection_name=collection, query=query
            )
            if not document:
                continue

            if answer := document.meta.get("answer", ""):
                # 设置来源信息
                source_info = document.meta.get("source", {})
                file_path = (
                    source_info.get("file_path", "")
                    if isinstance(source_info, dict)
                    else ""
                )
                if file_path:
                    self.handler.set_source(f"{collection}-{file_path}")
                else:
                    self.handler.set_source(collection)

                async for item in self._yield_stream(answer, "Exact match answer"):
                    yield item
                return
