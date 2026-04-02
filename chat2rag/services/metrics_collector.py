import asyncio
from time import perf_counter_ns
from typing import Dict, List

from chat2rag.core.logger import get_logger
from chat2rag.models.action import RobotAction
from chat2rag.models.expression import RobotExpression
from chat2rag.schemas.chat import QueryContent, SourceItem, SourceType
from chat2rag.schemas.metric import MetricCreate
from chat2rag.services.metric_service import metric_service

logger = get_logger(__name__)


class MetricsCollector:
    def __init__(self, message_id: str):
        self.message_id = message_id
        self.start_time_ns = perf_counter_ns()
        self.metrics = MetricCreate(message_id=message_id)
        self._source_items: list[SourceItem] = []
        self._tool_sources: Dict[str, str] = {}
        self._retrieval_documents: Dict[str, List[Dict]] = {}
        self._first_response_marked = False

    def set_query_info(
        self,
        content: QueryContent,
        chat_id: str,
        chat_rounds: int = None,
        collections: str | list = None,
        retrieval_params: dict = {},
        model: str = None,
        prompt: str = None,
        precision_mode: bool = False,
        tools: list = [],
        extra_params: dict = {},
    ):
        self.metrics.question = content.text
        self.metrics.image = content.image

        self.metrics.chat_id = chat_id
        self.metrics.chat_rounds = chat_rounds

        if isinstance(collections, list):
            collections = ",".join(collections)
        if collections:
            self.metrics.collections = collections
        self.metrics.retrieval_params = retrieval_params

        if model:
            self.metrics.model = model

        if prompt:
            self.metrics.prompt = prompt

        self.metrics.precision_mode = precision_mode

        self.metrics.tools = ",".join(tools)

        self.metrics.extra_params = extra_params

    def mark_first_response(self) -> bool:
        if self._first_response_marked:
            return False

        elapsed_ns = perf_counter_ns() - self.start_time_ns
        self.metrics.first_response_ms = round(elapsed_ns / 1_000_000, 2)
        self._first_response_marked = True

        logger.info(f"First response time: {elapsed_ns / 1_000_000_000:.3f}s")
        return True

    def add_source(self, source_type: SourceType, display: str, detail: str = ""):
        self._source_items.append(
            SourceItem(type=source_type, display=display, detail=detail)
        )

    def set_source(self, source: str):
        self._source_items = [SourceItem(type=SourceType.LLM, display=source)]

    def set_tool_sources(self, tool_sources: Dict[str, str]):
        self._tool_sources = tool_sources

    def set_retrieval_documents(self, documents: Dict[str, List[Dict]]):
        self._retrieval_documents = documents

    def set_behavior(
        self,
        expression: RobotExpression | None = None,
        action: RobotAction | None = None,
    ):
        if expression:
            self.metrics.expression = expression
        if action:
            self.metrics.action = action

    def set_answer_media(self, image: str = "", video: str = ""):
        self.metrics.answer_image = image
        self.metrics.answer_video = video

    def set_answer(self, answer: str):
        self.metrics.answer = answer

    def add_tool_info(self, tool_name: str):
        elapsed_ns = perf_counter_ns() - self.start_time_ns
        self.metrics.tool_ms = round(elapsed_ns / 1_000_000, 2)

        if self.metrics.execute_tools:
            tools_list = self.metrics.execute_tools.split(",")
            if tool_name not in tools_list:
                tools_list.append(tool_name)
                self.metrics.execute_tools = ",".join(tools_list)
        else:
            self.metrics.execute_tools = tool_name

    def set_tool_arguments(self, arguments: dict):
        self.metrics.tool_arguments = arguments

    def set_tool_result(self, result: dict):
        self.metrics.tool_result = result

    def add_tokens(self, input_tokens: int = 0, output_tokens: int = 0):
        self.metrics.input_tokens += input_tokens
        self.metrics.output_tokens += output_tokens

    def set_error(self, error_message: str):
        self.metrics.error_message = error_message

    async def save(self):
        try:
            elapsed_ns = perf_counter_ns() - self.start_time_ns
            self.metrics.total_ms = round(elapsed_ns / 1_000_000, 2)

            if self._source_items:
                self.metrics.source = [item.model_dump() for item in self._source_items]

            if self._retrieval_documents:
                self.metrics.retrieval_documents = self._retrieval_documents
                self.metrics.document_count = sum(
                    len(docs) for docs in self._retrieval_documents.values()
                )

            await metric_service.create(self.metrics)
            logger.info(f"Metrics saved: message_id={self.message_id}")

        except Exception:
            logger.exception(f"Failed to save metrics for {self.message_id}")

    def get_elapsed_ms(self) -> float:
        elapsed_ns = perf_counter_ns() - self.start_time_ns
        return round(elapsed_ns / 1_000_000, 2)
