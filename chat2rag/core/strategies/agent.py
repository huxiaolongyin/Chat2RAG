import asyncio
from datetime import datetime
from time import perf_counter
from typing import AsyncIterator, List

from haystack.dataclasses import ChatMessage, StreamingChunk

from chat2rag.core.pipelines.agent import AgentPipeline
from chat2rag.logger import get_logger
from chat2rag.utils.chat_history import ChatHistory
from chat2rag.utils.pipeline_cache import create_pipeline

from .base import ResponseStrategy

logger = get_logger(__name__)
chat_history = ChatHistory()


class AgentStrategy(ResponseStrategy):
    """Agent 兜底策略"""

    async def can_handle(self, query: str) -> bool:
        # Agent 作为兜底策略，总是可以处理
        return True

    async def execute(self, query: str) -> AsyncIterator[str]:
        history_messages = await chat_history.get_history_messages(
            self.request.prompt_name, self.request.chat_id, self.request.chat_rounds
        )

        asyncio.create_task(self._process_pipeline(query, history_messages))

        async for chunk in self.handler.get_stream(self.is_batch):
            yield chunk

    async def _process_pipeline(self, query: str, history_messages: list):
        """处理 Agent Pipeline"""
        try:
            pipeline = await create_pipeline(
                AgentPipeline,
                collections=self.request.collections,
                model=self.request.model,
                tools=self.request.tools,
            )

            result = await pipeline.run(
                query=query,
                top_k=self.request.top_k,
                score_threshold=self.request.score_threshold,
                doc_type="qa_pair",
                messages=history_messages,
                extra_params=self.request.extra_params
                | {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
                streaming_callback=self.handler.callback,
            )

            # 更新聊天历史
            messages: list = result.get("agent", {}).get("messages", [])
            if self.request.chat_id and messages:
                new_messages = self._get_latest_user_round(messages)
                chat_history.add_message(self.request.chat_id, messages=new_messages)

                logger.info(
                    f"Agent pipeline processed successfully. "
                    f"Answer:({new_messages[-1].text}) Cost: %.2fs",
                    perf_counter() - self.start_time,
                )

        except Exception as e:
            logger.error("Error in pipeline: %s", str(e))
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
