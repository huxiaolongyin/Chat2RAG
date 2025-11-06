import asyncio
from typing import AsyncIterator

from haystack.dataclasses import ChatRole, StreamingChunk

from chat2rag.config import CONFIG
from chat2rag.core.pipelines.rag_pipeline import RAGPipeline
from chat2rag.logger import get_logger
from chat2rag.models.models import ModelProvider, ModelSource
from chat2rag.services.model_service import ModelSourceService
from chat2rag.utils.chat_history import ChatHistory
from chat2rag.utils.merge_kwargs import merge_generation_kwargs
from chat2rag.utils.pipeline_cache import create_pipeline

from .base import ResponseStrategy

logger = get_logger(__name__)
model_source_service = ModelSourceService()
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
            enable_extra_prompt=False,
        )

        asyncio.create_task(self._process_pipeline(query, history_messages))

        async for chunk in self.handler.get_stream(self.is_batch):
            yield chunk

    async def _process_pipeline(self, query: str, history_messages: list):
        model_source: ModelSource = await model_source_service.get_best_source(
            self.request.model
        )
        model_provider: ModelProvider = await model_source.provider
        generation_kwargs = merge_generation_kwargs(
            self.request.generation_kwargs,
            model_source.generation_kwargs,
            CONFIG.GENERATION_KWARGS,
        )
        try:
            pipeline = await create_pipeline(
                RAGPipeline,
                intention_model=model_source.name,
                generator_model=model_source.name,
                api_base_url=model_provider.base_url,
                api_key=model_provider.api_key,
                generation_kwargs=generation_kwargs,
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

            # 更新 token 消费
            latest_messages = result["generator"]["replies"][0]
            input_tokens = 0
            output_tokens = 0
            input_tokens += int(
                latest_messages.meta.get("usage", {}).get("prompt_tokens", 0)
            )
            output_tokens += int(
                latest_messages.meta.get("usage", {}).get("completion_tokens", 0)
            )
            self.handler.set_token_info(input_tokens, output_tokens)

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
