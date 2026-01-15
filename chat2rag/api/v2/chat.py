import json
from time import perf_counter
from typing import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pyinstrument import Profiler

from chat2rag.core.enums import ProcessType
from chat2rag.core.logger import get_logger
from chat2rag.schemas.chat import ChatRequest
from chat2rag.strategies import (
    AgentStrategy,
    CommandStrategy,
    ExactMatchStrategy,
    FlowStrategy,
    MultiModalStrategy,
    SensitiveWordStrategy,
    StrategyChain,
)
from chat2rag.utils.stream import StreamHandler

logger = get_logger(__name__)
router = APIRouter()


class ChatProcessor:
    """聊天处理器：封装整个聊天流程"""

    def __init__(self, request: ChatRequest):
        self.request = request
        self.handler = StreamHandler()
        self.start_time = perf_counter()
        self.is_batch = request.batch_or_stream == ProcessType.BATCH
        self.query = self.request.content.text

    async def process(self) -> AsyncIterator[str]:
        """处理聊天请求"""
        # profiler = Profiler()
        # profiler.start()
        # once = True
        await self.handler.start()
        self._record_info()

        # 构建策略链并执行
        strategy_chain = self._build_strategy_chain()
        async for chunk in strategy_chain.execute(self.query):
            # if once:

            #     once = False
            yield chunk
        # profiler.stop()
        # print(
        #     profiler.output_text(
        #         unicode=True,
        #         color=True,
        #         show_all=False,
        #         timeline=False,
        #         short_mode=True,
        #     )
        # )

    def _build_strategy_chain(self) -> StrategyChain:
        """构建策略链"""
        return StrategyChain(
            [
                SensitiveWordStrategy(self.request, self.handler, self.start_time, self.is_batch),
                CommandStrategy(self.request, self.handler, self.start_time, self.is_batch),
                FlowStrategy(self.request, self.handler, self.start_time, self.is_batch),
                ExactMatchStrategy(self.request, self.handler, self.start_time, self.is_batch),
                MultiModalStrategy(self.request, self.handler, self.start_time, self.is_batch),
                AgentStrategy(self.request, self.handler, self.start_time, self.is_batch),
            ]
        )

    def _record_info(self):
        """记录聊天信息"""
        retrieval_params = {
            "top_k": self.request.top_k,
            "score_threshold": self.request.score_threshold,
        }
        # content = json.dumps(self.request.content, ensure_ascii=False)

        self.handler.set_query_info(
            content=self.request.content,
            chat_id=self.request.chat_id,
            chat_rounds=self.request.chat_rounds,
            collections=self.request.collections,
            retrieval_params=retrieval_params,
            model=self.request.model,
            prompt=self.request.prompt_name,
            precision_mode=self.is_batch,
            tools=self.request.tools,
            extra_params=self.request.extra_params,
        )


@router.post("/chat")
async def chat(chat_request: ChatRequest):
    """聊天接口"""

    # TODO: 临时补丁
    # chat_request.tools = [
    #     "navigate_to_location",
    #     "maps_weather",
    #     "maps_geo",
    #     "maps_direction_transit_integrated",
    #     "web_search",
    #     "cart_manage",
    #     "checkout",
    # ]

    processor = ChatProcessor(chat_request)
    return StreamingResponse(processor.process(), media_type="text/event-stream")
