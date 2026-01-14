import asyncio
from datetime import datetime
from time import perf_counter
from typing import AsyncIterator, List

from haystack.dataclasses import ChatMessage, ChatRole, StreamingChunk

from chat2rag.config import CONFIG
from chat2rag.core.pipelines.agent import AgentPipeline
from chat2rag.logger import get_logger
from chat2rag.models.models import ModelProvider, ModelSource
from chat2rag.services.model_service import ModelSourceService
from chat2rag.utils.chat_history import chat_history
from chat2rag.utils.merge_kwargs import merge_generation_kwargs
from chat2rag.utils.pipeline_cache import create_pipeline

from .base import ResponseStrategy

logger = get_logger(__name__)
model_source_service = ModelSourceService()


class AgentStrategy(ResponseStrategy):
    """Agent 兜底策略"""

    async def can_handle(self, query: str) -> bool:
        # Agent 作为兜底策略，总是可以处理
        return True

    async def execute(self, query: str) -> AsyncIterator[str]:
        history_messages = await chat_history.get_history_messages(
            self.request.prompt_name,
            self.request.chat_id,
            self.request.chat_rounds,
            image=self.request.content.get("image", ""),
        )
        asyncio.create_task(self._process_pipeline(query, history_messages))

        async for chunk in self.handler.get_stream(self.is_batch):
            yield chunk

    async def _process_pipeline(self, query: str, history_messages: List[ChatMessage]):
        """处理 Agent Pipeline"""

        # 获取当前时间
        current_time = {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        model_source: ModelSource = await model_source_service.get_best_source(
            self.request.model, extra_log="Agent Stage"
        )
        model_provider: ModelProvider = await model_source.provider
        generation_kwargs = merge_generation_kwargs(
            self.request.generation_kwargs,
            model_source.generation_kwargs,
            CONFIG.GENERATION_KWARGS,
        )
        try:
            pipeline = await create_pipeline(
                AgentPipeline,
                collections=self.request.collections,
                model=model_source.name,
                tools=self.request.tools,
                api_base_url=model_provider.base_url,
                api_key=model_provider.api_key,
                generation_kwargs=generation_kwargs,
            )

            result = await pipeline.run(
                query=query,
                top_k=self.request.top_k,
                score_threshold=self.request.score_threshold,
                filters={"field": "meta.type", "operator": "==", "value": "qa_pair"},
                messages=history_messages,
                extra_params=self.request.extra_params | current_time,
                streaming_callback=self.handler.callback,
            )

            # 更新聊天历史
            messages: list = result.get("agent", {}).get("messages", [])
            new_messages = self._get_latest_user_round(messages)
            if self.request.chat_id and messages:
                chat_history.add_message(self.request.chat_id, messages=new_messages)

                logger.info(
                    f"Agent pipeline processed successfully. " f"Answer:({new_messages[-1].text}) Cost: %.2fs",
                    perf_counter() - self.start_time,
                )

            # 更新 token 消费
            input_tokens = 0
            output_tokens = 0
            for message in new_messages:
                if message.role == ChatRole.ASSISTANT:
                    usage = message.meta.get("usage", {})
                    if usage:
                        input_tokens += int(usage.get("prompt_tokens", 0))
                        output_tokens += int(usage.get("completion_tokens", 0))
            self.handler.set_token_info(input_tokens, output_tokens)

        except Exception as e:
            logger.error("Error in pipeline: %s", str(e))
            self.handler.set_error(str(e))
            await self.handler.callback(
                StreamingChunk(
                    content="交互发生了一点小问题，等待工程师爸爸修复",
                    meta={"model": "error", "finish_reason": "error"},
                )
            )
        finally:
            await self.handler.finish()

    @staticmethod
    def _get_latest_user_round(messages: List[ChatMessage]) -> List[ChatMessage]:
        """获取最新一轮对话"""
        if not messages:
            return []

        # 从后往前找最后一个 user 消息的位置
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].role == "user":
                return messages[i:]

        return []
