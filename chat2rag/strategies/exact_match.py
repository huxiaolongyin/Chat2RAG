import os
from typing import AsyncIterator

from chat2rag.schemas.chat import SourceType
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
                source_info = document.meta.get("source", {})
                file_path = (
                    source_info.get("file_path", "")
                    if isinstance(source_info, dict)
                    else ""
                )
                if file_path:
                    file_name = os.path.basename(file_path)
                    self.handler.add_source(
                        SourceType.DOCUMENT, file_name, f"{collection}/{file_path}"
                    )
                else:
                    self.handler.add_source(SourceType.DOCUMENT, collection)

                async for item in self._yield_stream(answer, "Exact match answer"):
                    yield item
                return
