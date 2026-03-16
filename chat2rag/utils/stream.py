import asyncio
import copy
import json
import re
import uuid
from time import perf_counter
from typing import Dict

from haystack.dataclasses import StreamingChunk

from chat2rag.core.logger import get_logger
from chat2rag.dataclass.stream import StreamConfig
from chat2rag.models.action import RobotAction
from chat2rag.models.expression import RobotExpression
from chat2rag.schemas.chat import (
    BehaviorSchema,
    ContentSchema,
    QueryContent,
    StreamChunkV1,
    StreamChunkV2,
    ToolSchema,
)
from chat2rag.schemas.metric import MetricCreate
from chat2rag.services.action_service import robot_action_service
from chat2rag.services.expression_service import robot_expression_service
from chat2rag.services.metric_service import metric_service

logger = get_logger(__name__)

# Define compiled regular expressions at module level
EMOJI_PATTERN = re.compile(r"\[EMOJI:(.*?)\]")
ACTION_PATTERN = re.compile(r"\[ACTION:(.*?)\]")
LINK_PATTERN = re.compile(r"\[LINK:(.*?)\]")
IMAGE_PATTERN = re.compile(r"\[IMAGE:(.*?)\]")
BEHAVIOR_TAG_PATTERN = re.compile(r"\[(EMOJI|ACTION|LINK|IMAGE):.*?\]")


# Define constants at module level
class StreamControl:
    START = "[START]"
    END = "[END]"
    DOC_INFO = "doc_info"


class StreamHandler:
    """
    Handles streaming responses with metrics collection and behavior parsing.
    """

    def __init__(self, config: StreamConfig | None = None):
        self.stream_start = perf_counter()
        self.queue = asyncio.Queue()
        self.model = None
        self.config = config or StreamConfig()
        self.doc_length = 0
        self.message_id = str(uuid.uuid4().hex[:16])

        self.metrics = MetricCreate(message_id=self.message_id)

        self._execute_tools_list = []
        self._answer_parts = []
        self._source = ""
        self._tool_sources: Dict[str, str] = {}

    async def callback(self, chunk: StreamingChunk):
        await self.queue.put(chunk)

    async def set_doc_info(self, doc_count: int):
        await self.queue.put({"type": "doc_info", "count": doc_count})
        self.metrics.document_count = doc_count

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
        """
        Set query information for metrics tracking.
        """
        # Question
        self.metrics.question = content.text
        self.metrics.image = content.image

        # Conversation information
        self.metrics.chat_id = chat_id
        self.metrics.chat_rounds = chat_rounds

        # Knowledge base
        if isinstance(collections, list):
            collections = ",".join(collections)
        if collections:
            self.metrics.collections = collections
        self.metrics.retrieval_params = retrieval_params

        # Model
        if model:
            self.metrics.model = model
            self.model = model

        # Prompt
        if prompt:
            self.metrics.prompt = prompt

        # Precision Mode
        self.metrics.precision_mode = precision_mode

        # Tools
        self.metrics.tools = ",".join(tools)

        # Extra parameters
        self.metrics.extra_params = extra_params

    def set_tool_info(self, tools: str | None = None):
        """Set executed tool information"""
        if tools:
            self._execute_tools_list.append(tools)
            self.metrics.execute_tools = ",".join(self._execute_tools_list)

            # TODO: Temporary measure
            self.metrics.tool_ms = round((perf_counter() - self.stream_start) * 1000, 2)

    def set_token_info(self, input_tokens: int = 0, output_tokens: int = 0):
        """Set token information"""
        self.metrics.input_tokens += input_tokens
        self.metrics.output_tokens += output_tokens

    def set_source(self, source: str):
        """Set information source"""
        self._source = source

    def set_tool_sources(self, tool_sources: Dict[str, str]):
        """Set tool sources mapping {tool_name: mcp_server_name}"""
        self._tool_sources = tool_sources

    def set_behavior(
        self,
        expression: RobotExpression | None = None,
        action: RobotAction | None = None,
    ):
        """Set behavior data"""
        if expression:
            self.metrics.expression = expression
        if action:
            self.metrics.action = action

    def set_error(self, error_message: str):
        """Set error information"""
        self.metrics.error_message = error_message

    async def save_metrics(self):
        """Save metrics to database"""
        try:
            # Calculate total response time
            total_time = perf_counter() - self.stream_start
            self.metrics.total_ms = round(total_time * 1000, 2)

            # Create metric record
            await metric_service.create(self.metrics)
            logger.info(f"Performance metrics saved: message_id={self.message_id}")

        except Exception as e:
            logger.exception(f"Failed to save metrics for {self.message_id}")

    async def _parse_behavior_tags(self, text: str):
        """
        Extract behavior tags from the text and return the cleaned text
        TODO: Handle streaming return
        """
        emojis = EMOJI_PATTERN.findall(text)
        actions = ACTION_PATTERN.findall(text)
        links = LINK_PATTERN.findall(text)
        images = IMAGE_PATTERN.findall(text)

        # Remove all tags, keep plain text only
        clean_text = BEHAVIOR_TAG_PATTERN.sub("", text).strip()
        emoji = await robot_expression_service.get_code_by_name(next(iter(emojis), ""))
        action = await robot_action_service.get_code_by_name(next(iter(actions), ""))

        # Save expression and action
        self.set_behavior(emoji, action)

        return {
            "emoji": emoji.code if emoji else "",
            "action": action.code if action else "",
            "link": next(iter(links), ""),
            "image": next(iter(images), ""),
            "clean_text": clean_text,
        }

    async def _create_message(
        self,
        content: str,
        meta: dict = None,
        tool: str = None,
        arguments: dict = {},
        tool_result: dict = {},
        is_start: int = 0,
        query: dict = {},
    ) -> StreamChunkV2:
        """Create message format"""
        if meta is None:
            meta = {"model": "None", "finish_reason": "none"}

        tool_type = ""
        command = meta.get("command", "")
        if command:
            tool = command
            tool_type = "command"
        if meta.get("finish_reason") == "stop":
            status = 2
        elif is_start:
            status = 0
        else:
            status = 1

        # Parse behavior tags
        behavior_data = (
            await self._parse_behavior_tags(content)
            if content
            else {"clean_text": "", "emoji": "", "action": "", "link": "", "image": ""}
        )
        clean_content = behavior_data["clean_text"]

        # Accumulate answer content
        if content:
            self._answer_parts.append(clean_content)
            self.metrics.answer = "".join(self._answer_parts)

        if tool:
            tool_content = ToolSchema(
                tool_name=tool,
                tool_type=tool_type,
                arguments=arguments,
                tool_result=tool_result,
            )
        else:
            tool_content = {}

        return StreamChunkV2(
            input=query,
            content=ContentSchema(
                text=behavior_data["clean_text"], image=behavior_data["image"]
            ),
            model=self.model,
            status=status,
            behavior=BehaviorSchema(
                emoji=behavior_data["emoji"], action=behavior_data["action"]
            ),
            tool=tool_content,
            link=behavior_data["link"],
            source=self._source,
            document_count=self.doc_length,
            message_id=self.message_id,
        )

    def _should_flush_batch(self, chunk: str, batch_content: str) -> bool:
        """
        Determine whether to flush the current batch
        """
        return (
            chunk.content in self.config.split_symbols
            or chunk.content.rstrip() in self.config.split_symbols
            or len(batch_content) >= self.config.batch_size
        )

    def _is_split_punctuation(self, char):
        """Check if character is a split punctuation mark, including Chinese and English punctuation"""
        return char in self.config.split_symbols

    def _handle_first_response(self):
        """Handle first response and record time metrics"""
        elapsed = perf_counter() - self.stream_start
        self.metrics.first_response_ms = round(elapsed * 1000, 2)
        logger.info(f"Handle first response time: {elapsed:.3f}s")
        return False

    async def _yield_data(self, content="", meta=None, **kwargs):
        """Generate and send data"""
        data = await self._create_message(content, meta, **kwargs)
        yield f"data: {json.dumps(data.model_dump(by_alias=True), ensure_ascii=False)}\n\n"

    async def _handle_tool_call(self, chunk):
        """Handle tool call information"""
        tool_call = chunk.meta.get("tool_call", {})
        tool_result = chunk.meta.get("tool_result", {})
        tool_name = ""
        arguments = {}

        if tool_call:
            tool_name = tool_call.tool_name
            arguments = tool_call.arguments

            # Record tool call information
            self.set_tool_info(tool_name)

        if tool_result:
            try:
                tool_result = json.loads(str(tool_result))
                tool_result.get("content")[0]["text"] = json.loads(
                    tool_result.get("content")[0]["text"]
                )
                tool_result["content"] = tool_result.get("content")[0]

            except Exception:
                logger.warning(
                    "Failed to parse tool call result as JSON. Using original result"
                )

            # Record tool result
            self.metrics.tool_result = (
                tool_result if isinstance(tool_result, dict) else {}
            )

        async for data_str in self._yield_data(
            "", chunk.meta, tool=tool_name, arguments=arguments, tool_result=tool_result
        ):
            yield data_str

    async def _process_batch_content(self, chunk, current_batch, first_response):
        """Process content in batch mode"""
        content = chunk.content
        last_split_pos = 0
        results = []

        for i, char in enumerate(content):
            if self._is_split_punctuation(char):
                split_chunk = copy.copy(chunk)
                split_chunk.content = content[last_split_pos : i + 1]
                current_batch.append(split_chunk)

                batch_content = "".join([c.content for c in current_batch])
                if first_response:
                    first_response = self._handle_first_response()

                # Collect data instead of yielding
                async for data_str in self._yield_data(batch_content, chunk.meta):
                    results.append(data_str)

                current_batch.clear()
                last_split_pos = i + 1

        if last_split_pos < len(content):
            remaining_chunk = copy.copy(chunk)
            remaining_chunk.content = content[last_split_pos:]
            current_batch.append(remaining_chunk)

        return first_response, results

    async def get_stream(self, is_batch: bool = False, query: dict = {}):
        first_response = True  # Add flag to track first response
        current_batch = []

        while True:
            chunk = await self.queue.get()

            # Handle special control messages
            if isinstance(chunk, dict) and chunk.get("type") == "doc_info":
                self.doc_length = chunk["count"]
                continue

            if chunk == StreamControl.START:
                async for data_str in self._yield_data("", is_start=1, query=query):
                    yield data_str
                continue

            if chunk == StreamControl.END:
                if self._execute_tools_list:
                    sources = []
                    seen = set()
                    for tool_name in self._execute_tools_list:
                        if tool_name in seen:
                            continue
                        seen.add(tool_name)
                        server_name = self._tool_sources.get(tool_name, "")
                        if server_name:
                            sources.append(f"{server_name} ({tool_name})")
                    if sources:
                        self._source = ", ".join(sources)

                if is_batch and current_batch:
                    combined_content = "".join([c.content for c in current_batch])

                    async for data_str in self._yield_data(
                        combined_content, current_batch[-1].meta
                    ):
                        yield data_str

                if is_batch:
                    async for data_str in self._yield_data(
                        "", meta={"finish_reason": "stop", "model": ""}
                    ):
                        yield data_str

                logger.debug("Received END signal, saving metrics")
                await self.save_metrics()
                logger.debug("Metrics saved successfully")
                break

            if not self.model:
                self.model = chunk.meta.get("model", "")
                self.metrics.model = self.model

            if chunk.meta.get("tool_call") or chunk.meta.get("tool_result"):
                async for item in self._handle_tool_call(chunk):
                    yield item
                continue

            # Process content
            if not is_batch:
                # Single streaming mode
                if first_response:
                    first_response = self._handle_first_response()

                    async for data_str in self._yield_data(chunk.content, chunk.meta):
                        yield data_str
                    continue
                if chunk.content or chunk.meta.get("finish_reason") == "stop":
                    async for data_str in self._yield_data(chunk.content, chunk.meta):
                        yield data_str

            else:
                # Batch processing mode
                first_response, results = await self._process_batch_content(
                    chunk, current_batch, first_response
                )
                for data_str in results:
                    yield data_str

    async def start(self):
        await self.queue.put(StreamControl.START)

    async def finish(self):
        await self.queue.put(StreamControl.END)


class StreamHandlerV1(StreamHandler):
    async def _create_message(self, *args, **kwargs) -> StreamChunkV1:
        """创建消息格式"""
        res: StreamChunkV2 = await super()._create_message(*args, **kwargs)
        return res.to_stream_chunk_v1()
