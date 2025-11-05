import asyncio
from typing import AsyncIterator

from haystack.dataclasses import ChatRole, StreamingChunk

from chat2rag.core.pipelines.rag_pipeline import RAGPipeline
from chat2rag.logger import get_logger
from chat2rag.utils.chat_history import ChatHistory
from chat2rag.utils.pipeline_cache import create_pipeline

from .base import ResponseStrategy

logger = get_logger(__name__)
chat_history = ChatHistory()


class RAGStrategy(ResponseStrategy):
    async def can_handle(self, query: str) -> bool:
        # RAG 作为兜底策略，总是可以处理
        return True

    async def execute(self, query: str) -> AsyncIterator[str]:
        history_messages = await chat_history.get_history_messages(
            self.request.prompt_name,
            self.request.chat_id,
            self.request.chat_rounds,
            tag_get=False,
        )

        asyncio.create_task(self._process_pipeline(query, history_messages))

        async for chunk in self.handler.get_stream(self.is_batch):
            yield chunk

    async def _process_pipeline(self, query: str, history_messages: list):
        try:
            pipeline = await create_pipeline(
                RAGPipeline,
                intention_model=self.request.intention_model,
                generator_model=self.request.model,
            )

            result = await pipeline.run(
                query=query,
                top_k=self.request.top_k,
                score_threshold=self.request.score_threshold,
                messages=history_messages,
                generation_kwargs=self.request.generation_kwargs,
                streaming_callback=self.handler.callback,
                start_time=self.start_time,
                qdrant_index=self.request.collections[0],
            )

            # 更新聊天历史
            if self.request.chat_id:
                chat_history.add_message(
                    self.request.chat_id,
                    ChatRole.USER,
                    self.query,
                )
                chat_history.add_message(
                    self.request.chat_id,
                    ChatRole.ASSISTANT,
                    result["generator"]["replies"][0].text,
                )
        except Exception as e:
            logger.error("Error in exact query processing: %s", str(e))
            await self.handler.callback(
                StreamingChunk(
                    content=f"精确查询处理错误: {str(e)}",
                    meta={"model": "error", "finish_reason": "error"},
                )
            )

        finally:
            await self.handler.finish()
