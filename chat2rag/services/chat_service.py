from time import perf_counter
from typing import AsyncIterator

from chat2rag.core.enums import ProcessType
from chat2rag.schemas.chat import ChatRequest
from chat2rag.services.question_analyzer import QuestionAnalyzer
from chat2rag.strategies import (
    AgentStrategy,
    CommandStrategy,
    ExactMatchStrategy,
    FlowStrategy,
    MultiModalStrategy,
    SensitiveWordStrategy,
    StrategyChain,
)
from chat2rag.utils.stream import StreamHandler, StreamHandlerV1


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

        await self.handler.start()
        self._record_info()

        # 构建策略链并执行
        strategy_chain = self._build_strategy_chain()
        async for chunk in strategy_chain.execute(self.query):
            yield chunk

        # 记录热门问题分析
        question_analyzer = QuestionAnalyzer()
        await question_analyzer.add_or_update_question(
            ",".join(self.request.collections), question_text=self.query
        )
        question_analyzer._save_checkpoint()

    def _build_strategy_chain(self) -> StrategyChain:
        """构建策略链"""
        return StrategyChain(
            [
                SensitiveWordStrategy(
                    self.request, self.handler, self.start_time, self.is_batch
                ),
                CommandStrategy(
                    self.request, self.handler, self.start_time, self.is_batch
                ),
                FlowStrategy(
                    self.request, self.handler, self.start_time, self.is_batch
                ),
                ExactMatchStrategy(
                    self.request, self.handler, self.start_time, self.is_batch
                ),
                MultiModalStrategy(
                    self.request, self.handler, self.start_time, self.is_batch
                ),
                AgentStrategy(
                    self.request, self.handler, self.start_time, self.is_batch
                ),
            ]
        )

    def _record_info(self):
        """记录聊天信息"""
        retrieval_params = {
            "top_k": self.request.top_k,
            "score_threshold": self.request.score_threshold,
        }

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


class ChatProcessorV1(ChatProcessor):
    def __init__(self, request: ChatRequest):
        super().__init__(request)
        self.handler = StreamHandlerV1()

    def _build_strategy_chain(self) -> StrategyChain:
        """构建策略链"""
        # TODO: 定制化需求
        if "福州火车南站" in self.request.collections:
            self.request.tools = ["get_train_info"]

        return StrategyChain(
            [
                ExactMatchStrategy(
                    self.request, self.handler, self.start_time, self.is_batch
                ),
                AgentStrategy(
                    self.request, self.handler, self.start_time, self.is_batch
                ),
            ]
        )
