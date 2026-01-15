import asyncio
from abc import ABC, abstractmethod
from time import perf_counter
from typing import AsyncIterator

from haystack.dataclasses import ChatRole, StreamingChunk

from chat2rag.dataclass.strategy import StrategyRequest
from chat2rag.logger import get_logger
from chat2rag.utils.chat_history import chat_history
from chat2rag.utils.stream import StreamHandler

logger = get_logger(__name__)


class ResponseStrategy(ABC):
    """响应策略基类"""

    def __init__(
        self,
        request: StrategyRequest,
        handler: StreamHandler,
        start_time: float,
        is_batch: bool,
    ):
        self.request = request
        self.handler = handler
        self.start_time = start_time
        self.is_batch = is_batch
        self.query = self.request.content.text

    @abstractmethod
    async def can_handle(self, query: str) -> bool:
        """判断是否能处理该查询"""
        pass

    @abstractmethod
    async def execute(self, query: str) -> AsyncIterator[str]:
        """执行策略并返回流式结果"""
        pass

    async def _yield_stream(self, answer: str, source: str, **kwargs) -> AsyncIterator[str]:
        """统一的流式输出"""
        asyncio.create_task(self._stream_answer(answer, source, **kwargs))
        async for chunk in self.handler.get_stream(self.is_batch, query={"text": self.query}):
            yield chunk

    async def _stream_answer(self, answer: str, source: str, **kwargs):
        """流式发送答案"""

        try:
            logger.debug(f"Processing {source}: {answer}")

            # 逐字发送答案
            for i in range(0, len(answer), 1):
                chunk = answer[i : i + 1]
                await self.handler.callback(
                    StreamingChunk(
                        content=chunk,
                        meta={"model": "", "answer_source": source, "finish_reason": "none", **kwargs},
                    )
                )
                await asyncio.sleep(0.001)

            # 发送结束信号
            await self.handler.callback(
                StreamingChunk(
                    content="",
                    meta={"model": "", "answer_source": source, "finish_reason": "stop"},
                )
            )

            # 更新聊天历史
            if self.request.chat_id:
                chat_history.add_message(self.request.chat_id, ChatRole.USER, self.query)
                chat_history.add_message(self.request.chat_id, ChatRole.ASSISTANT, answer)

            logger.info(f"{source} processed successfully, took %.2fs", perf_counter() - self.start_time)

        except Exception as e:
            logger.error(f"Error in {source} processing: %s", str(e))
            await self.handler.callback(
                StreamingChunk(content=f"处理错误: {str(e)}", meta={"model": "error", "finish_reason": "error"})
            )
        finally:
            await self.handler.finish()


class StrategyChain:
    """策略链：按顺序执行策略，直到有策略成功处理"""

    def __init__(self, strategies: list[ResponseStrategy]):
        self.strategies = strategies

    async def execute(self, query: str) -> AsyncIterator[str]:
        """按顺序执行策略"""
        for strategy in self.strategies:
            if await strategy.can_handle(query):
                has_result = False
                async for chunk in strategy.execute(query):
                    has_result = True
                    yield chunk

                # 如果该策略产生了结果，就不再执行后续策略
                if has_result:
                    return
