from time import perf_counter
from typing import AsyncIterator

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from chat2rag.core.strategies import ExactMatchStrategy, RAGStrategy, StrategyChain
from chat2rag.enums import ProcessType
from chat2rag.logger import get_logger
from chat2rag.schemas.chat import ChatQueryParams
from chat2rag.utils.stream_v1 import StreamHandlerV1

logger = get_logger(__name__)
router = APIRouter()


class ChatProcessor:
    """聊天处理器：封装整个聊天流程"""

    def __init__(self, params: ChatQueryParams, batch_or_stream: ProcessType):
        self.params = params
        self.handler = StreamHandlerV1()
        self.start_time = perf_counter()
        self.is_batch = batch_or_stream == ProcessType.BATCH

    async def process(self) -> AsyncIterator[str]:
        """处理聊天请求"""
        await self.handler.start()
        self._record_info()

        # 构建策略链并执行
        strategy_chain = self._build_strategy_chain()
        async for chunk in strategy_chain.execute(self.params.query):
            yield chunk

    def _build_strategy_chain(self) -> StrategyChain:
        """构建策略链"""
        return StrategyChain(
            [
                ExactMatchStrategy(
                    self.params.to_strategy_request(),
                    self.handler,
                    self.start_time,
                    self.is_batch,
                ),
                RAGStrategy(
                    self.params.to_strategy_request(),
                    self.handler,
                    self.start_time,
                    self.is_batch,
                ),
            ]
        )

    def _record_info(self):
        """记录聊天信息"""
        self.handler.set_chat_info(self.params.chat_id, self.params.chat_rounds)
        self.handler.set_query_info(
            question=self.params.query,
            model=self.params.generator_model,
            prompt=self.params.prompt_name,
            precision_mode=self.params.precision_mode,
        )
        self.handler.set_collection_info(self.params.collection_name)


@router.get("/query-stream", summary="大模型交互V1", deprecated=True)
async def chat(
    params: ChatQueryParams = Depends(),
    batch_or_stream: ProcessType = Query(ProcessType.BATCH, alias="batchOrStream"),
):
    """聊天V1接口"""

    processor = ChatProcessor(params, batch_or_stream)
    return StreamingResponse(processor.process(), media_type="text/event-stream")
