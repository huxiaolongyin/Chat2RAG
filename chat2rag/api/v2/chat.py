from time import perf_counter
from typing import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from chat2rag.core.strategies import (
    AgentStrategy,
    CommandStrategy,
    ExactMatchStrategy,
    FlowStrategy,
    StrategyChain,
)
from chat2rag.enums import ProcessType
from chat2rag.logger import auto_log, get_logger
from chat2rag.schemas.chat import ChatRequest
from chat2rag.utils.chat_history import ChatHistory
from chat2rag.utils.stream import StreamHandler

logger = get_logger(__name__)
router = APIRouter()
chat_history = ChatHistory()


class ChatProcessor:
    """聊天处理器：封装整个聊天流程"""

    def __init__(self, request: ChatRequest):
        self.request = request
        self.handler = StreamHandler()
        self.start_time = perf_counter()
        self.is_batch = request.batch_or_stream == ProcessType.BATCH
        self.query = self.request.content.get("text")

    async def process(self) -> AsyncIterator[str]:
        """处理聊天请求"""
        await self.handler.start()
        self._record_info()

        # 构建策略链并执行
        strategy_chain = self._build_strategy_chain()
        async for chunk in strategy_chain.execute(self.query):
            yield chunk

    def _build_strategy_chain(self) -> StrategyChain:
        """构建策略链"""
        return StrategyChain(
            [
                CommandStrategy(
                    self.request, self.handler, self.start_time, self.is_batch
                ),
                FlowStrategy(
                    self.request, self.handler, self.start_time, self.is_batch
                ),
                ExactMatchStrategy(
                    self.request, self.handler, self.start_time, self.is_batch
                ),
                AgentStrategy(
                    self.request, self.handler, self.start_time, self.is_batch
                ),
            ]
        )

    def _record_info(self):
        """记录聊天信息"""
        self.handler.set_chat_info(self.request.chat_id, self.request.chat_rounds)
        self.handler.set_query_info(self.query, self.request.prompt_name)
        self.handler.set_collection_info(self.request.collections)


@router.post("/chat")
@auto_log(level="info")
async def chat(chat_request: ChatRequest):
    """聊天接口"""

    # TODO: 临时补丁
    chat_request.model = "qwen3-235b-a22b-instruct-2507"
    chat_request.tools = [
        "navigate_to_location",
        "maps_weather",
        "maps_geo",
        "maps_direction_transit_integrated",
    ]
    chat_request.flows = ["点菜流程"]
    chat_request.chat_rounds = 5
    try:
        chat_request.chat_id = chat_request.chat_id.split("_")[1]
    except:
        pass

    processor = ChatProcessor(chat_request)
    return StreamingResponse(processor.process(), media_type="text/event-stream")
