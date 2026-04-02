import asyncio
import json
import uuid
from typing import AsyncIterator

from haystack.dataclasses import StreamingChunk

from chat2rag.core.logger import get_logger
from chat2rag.dataclass.stream import StreamConfig
from chat2rag.schemas.chat import (
    Audio,
    AudioContent,
    BehaviorSchema,
    ContentSchema,
    QueryContent,
    SourceSchema,
    SourceType,
    StreamChunkV2,
    ToolSchema,
)
from chat2rag.services.action_service import robot_action_service
from chat2rag.services.expression_service import robot_expression_service
from chat2rag.services.metrics_collector import MetricsCollector
from chat2rag.streaming.behavior_parser import BehaviorTagParser
from chat2rag.streaming.constants import BEHAVIOR_TAG_PATTERN
from chat2rag.streaming.mode_processor import create_mode_processor
from chat2rag.streaming.tool_handler import ToolCallHandler
from chat2rag.streaming.tts_processor import TTSProcessor
from chat2rag.providers.tts.factory import TTSFactory

logger = get_logger(__name__)


class StreamControl:
    START = "[START]"
    END = "[END]"
    DOC_INFO = "doc_info"


class StreamHandler:
    def __init__(
        self,
        config: StreamConfig | None = None,
        enable_tts: bool = False,
        audio_config: Audio | None = None,
    ):
        self.message_id = str(uuid.uuid4().hex[:16])
        self.config = config or StreamConfig()

        self.behavior_parser = BehaviorTagParser()
        self.metrics = MetricsCollector(self.message_id)
        self.tool_handler = ToolCallHandler()

        self.queue: asyncio.Queue = asyncio.Queue()
        self.model: str | None = None

        self._answer_parts: list[str] = []

        self.enable_tts = enable_tts
        self.tts_processor: TTSProcessor | None = None

        if enable_tts:
            audio_cfg = audio_config or Audio()
            tts_provider = TTSFactory.create(audio_cfg)
            if tts_provider:
                self.tts_processor = TTSProcessor(tts_provider, audio_cfg)

        self.audio_config = audio_config or Audio()
        self.mode_processor = None

    @property
    def _execute_tools_list(self) -> list[str]:
        """向后兼容：工具执行列表"""
        return self.tool_handler._executed_tools

    async def callback(self, chunk: StreamingChunk):
        await self.queue.put(chunk)

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
        self.metrics.set_query_info(
            content=content,
            chat_id=chat_id,
            chat_rounds=chat_rounds,
            collections=collections,
            retrieval_params=retrieval_params,
            model=model,
            prompt=prompt,
            precision_mode=precision_mode,
            tools=tools,
            extra_params=extra_params,
        )

        if model:
            self.model = model

    def set_tool_info(self, tools: str | None = None):
        if tools:
            self.metrics.add_tool_info(tools)

    def set_token_info(self, input_tokens: int = 0, output_tokens: int = 0):
        self.metrics.add_tokens(input_tokens, output_tokens)

    def set_source(self, source: str):
        self.metrics.set_source(source)

    def add_source(self, source_type: SourceType, display: str, detail: str = ""):
        self.metrics.add_source(source_type, display, detail)

    def set_tool_sources(self, tool_sources: dict):
        self.tool_handler.set_tool_sources(tool_sources)
        self.metrics.set_tool_sources(tool_sources)

    def set_retrieval_documents(self, documents: dict):
        self.metrics.set_retrieval_documents(documents)

    def set_behavior(self, expression=None, action=None):
        self.metrics.set_behavior(expression, action)

    def set_error(self, error_message: str):
        self.metrics.set_error(error_message)

    async def save_metrics(self):
        await self.metrics.save()

    async def start(self):
        await self.queue.put(StreamControl.START)

    async def finish(self):
        await self.queue.put(StreamControl.END)

    async def get_stream(
        self, is_batch: bool = False, query: dict = {}
    ) -> AsyncIterator[str]:
        self.mode_processor = create_mode_processor(is_batch, self.config.split_symbols)

        first_response_marked = False
        stream_ended = False

        logger.debug(f"[{self.message_id}] Stream started")

        try:
            while True:
                if stream_ended:
                    audio_queue_empty = True
                    if self.tts_processor:
                        audio_queue_empty = self.tts_processor._audio_queue.empty()
                    if audio_queue_empty:
                        break

                tasks = [asyncio.create_task(self.queue.get())]

                if self.tts_processor and self.tts_processor.is_running():
                    audio_task = asyncio.create_task(
                        self.tts_processor.get_audio(timeout=0.05)
                    )
                    tasks.append(audio_task)

                done, pending = await asyncio.wait(
                    tasks, return_when=asyncio.FIRST_COMPLETED
                )

                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

                for task in done:
                    result = task.result()

                    if len(tasks) == 1 or task == tasks[0]:
                        chunk = result

                        if chunk == StreamControl.START:
                            logger.debug(f"[{self.message_id}] Received START")

                            if self.tts_processor:
                                await self.tts_processor.start_worker()

                            async for data_str in self._yield_data(
                                "", is_start=1, query=query
                            ):
                                yield data_str
                            continue

                        if chunk == StreamControl.END:
                            logger.debug(f"[{self.message_id}] Received END")
                            stream_ended = True

                            combined_content, final_meta = await self._finalize_stream()
                            if combined_content:
                                async for data_str in self._yield_data(
                                    combined_content, final_meta
                                ):
                                    yield data_str

                            if self.tts_processor:
                                await self.tts_processor.stop_worker()

                                async for (
                                    audio_data
                                ) in self.tts_processor.drain_audio_queue():
                                    if audio_data:
                                        async for data_str in self._yield_audio_data(
                                            *audio_data
                                        ):
                                            yield data_str

                            async for data_str in self._yield_data(
                                "", meta={"finish_reason": "stop", "model": ""}
                            ):
                                yield data_str

                            await self.metrics.save()
                            logger.info(f"[{self.message_id}] Stream completed")
                            continue

                        if not self.model:
                            self.model = chunk.meta.get("model", "")
                            self.metrics.metrics.model = self.model

                        if chunk.meta.get("tool_call") or chunk.meta.get("tool_result"):
                            async for item in self._handle_tool_call(chunk):
                                yield item
                            continue

                        has_output, output_chunks = self.mode_processor.process_chunk(
                            chunk
                        )

                        if has_output:
                            for output_chunk in output_chunks:
                                async for data_str in self._process_content_chunk(
                                    output_chunk, first_response_marked
                                ):
                                    yield data_str
                                first_response_marked = (
                                    self.metrics._first_response_marked
                                )

                    elif len(tasks) > 1 and task == tasks[1]:
                        if result:
                            async for data_str in self._yield_audio_data(*result):
                                yield data_str

        finally:
            if self.tts_processor:
                await self.tts_processor.stop_worker()

    async def _finalize_stream(self):
        executed_tools = self.tool_handler.get_executed_tools()

        if executed_tools:
            source_items = self.tool_handler.generate_source_items()
            for item_dict in source_items:
                self.metrics.add_source(
                    item_dict["type"], item_dict["display"], item_dict["detail"]
                )

        accumulated_tags = self.behavior_parser.get_accumulated_tags()

        emoji_name = accumulated_tags.get("emoji", "")
        action_name = accumulated_tags.get("action", "")

        emoji_obj = await robot_expression_service.get_code_by_name(emoji_name)
        action_obj = await robot_action_service.get_code_by_name(action_name)

        self.metrics.set_behavior(emoji_obj, action_obj)
        self.metrics.set_answer_media(
            accumulated_tags.get("image", ""), accumulated_tags.get("video", "")
        )

        final_chunks = self.mode_processor.finalize()
        if final_chunks:
            combined_content = "".join([c.content for c in final_chunks])
            self._answer_parts.append(combined_content)
            self.metrics.set_answer("".join(self._answer_parts))

            if self.tts_processor and combined_content.strip():
                await self.tts_processor.add_text(combined_content)

            return combined_content, final_chunks[-1].meta

        return None, None

    async def _process_content_chunk(
        self, chunk: StreamingChunk, first_response_marked: bool
    ) -> AsyncIterator[str]:
        if not chunk.content:
            return

        clean_text, remaining, tags = self.behavior_parser.extract_tags(chunk.content)

        has_behavior = any(tags.values())

        if has_behavior:
            emoji_name = tags.get("emoji", "")
            action_name = tags.get("action", "")

            emoji_obj = await robot_expression_service.get_code_by_name(emoji_name)
            action_obj = await robot_action_service.get_code_by_name(action_name)

            if not first_response_marked:
                self.metrics.mark_first_response()

            behavior_data = {
                "clean_text": "",
                "emoji": emoji_obj.code if emoji_obj else "",
                "action": action_obj.code if action_obj else "",
                "image": tags.get("image", ""),
                "video": tags.get("video", ""),
            }

            async for data_str in self._yield_data(
                "", chunk.meta, behavior_data=behavior_data
            ):
                yield data_str

        if clean_text:
            if not first_response_marked:
                self.metrics.mark_first_response()

            behavior_data = {
                "clean_text": clean_text,
                "emoji": "",
                "action": "",
                "image": "",
                "video": "",
            }

            async for data_str in self._yield_data(
                clean_text, chunk.meta, behavior_data=behavior_data
            ):
                yield data_str

            if self.tts_processor and self.tts_processor.is_running():
                await self.tts_processor.add_text(clean_text)

    async def _handle_tool_call(self, chunk: StreamingChunk) -> AsyncIterator[str]:
        tool_name, arguments, tool_result = self.tool_handler.handle_tool_call(chunk)

        if tool_name:
            self.metrics.add_tool_info(tool_name)

        if arguments:
            self.metrics.set_tool_arguments(arguments)

        if tool_result:
            self.metrics.set_tool_result(tool_result)

        async for data_str in self._yield_data(
            "",
            chunk.meta,
            tool=tool_name,
            arguments=arguments,
            tool_result=tool_result,
        ):
            yield data_str

    async def _yield_data(
        self,
        content: str = "",
        meta: dict = None,
        audio_content: AudioContent | None = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        data = await self._create_message(
            content, meta, audio_content=audio_content, **kwargs
        )
        yield f"data: {json.dumps(data.model_dump(by_alias=True), ensure_ascii=False)}\n\n"

    async def _yield_audio_data(
        self, type_: str, text: str, audio_base64: str, meta: dict | None
    ) -> AsyncIterator[str]:
        audio_content = self.tts_processor.build_audio_content(text, audio_base64)
        async for data_str in self._yield_data("", meta, audio_content=audio_content):
            yield data_str

    async def _create_message(
        self,
        content: str,
        meta: dict = None,
        tool: str = None,
        arguments: dict = {},
        tool_result: dict = {},
        is_start: int = 0,
        query: dict = {},
        behavior_data: dict = None,
        audio_content: AudioContent | None = None,
    ) -> StreamChunkV2:
        if meta is None:
            meta = {"model": "None", "finish_reason": "none"}

        tool_type = ""
        command = meta.get("command", "")
        if command:
            tool = command
            tool_type = "command"
            if meta.get("arguments"):
                arguments = meta.get("arguments")

        if meta.get("finish_reason") == "stop":
            status = 2
        elif is_start:
            status = 0
        else:
            status = 1

        if behavior_data is None:
            if content:
                clean_text = BEHAVIOR_TAG_PATTERN.sub("", content).strip()

                clean_text, _, tags = self.behavior_parser.extract_tags(content)
                emoji_name = tags.get("emoji", "")
                action_name = tags.get("action", "")

                emoji_obj = await robot_expression_service.get_code_by_name(emoji_name)
                action_obj = await robot_action_service.get_code_by_name(action_name)

                behavior_data = {
                    "clean_text": clean_text,
                    "emoji": emoji_obj.code if emoji_obj else "",
                    "action": action_obj.code if action_obj else "",
                    "image": tags.get("image", ""),
                    "video": tags.get("video", ""),
                }
            else:
                behavior_data = {
                    "clean_text": "",
                    "emoji": "",
                    "action": "",
                    "image": "",
                    "video": "",
                }

        clean_content = behavior_data["clean_text"]

        if content:
            self._answer_parts.append(clean_content)
            self.metrics.set_answer("".join(self._answer_parts))

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
                text=behavior_data["clean_text"],
                image=behavior_data["image"],
                video=behavior_data["video"],
                audio=audio_content,
            ),
            model=self.model,
            status=status,
            behavior=BehaviorSchema(
                emoji=behavior_data["emoji"],
                action=behavior_data["action"],
            ),
            tool=tool_content,
            source=SourceSchema(items=self.metrics._source_items)
            if status == 2
            else SourceSchema(),
            document=self.metrics._retrieval_documents
            if self.metrics._retrieval_documents
            else {},
            message_id=self.message_id,
        )


class StreamHandlerV1(StreamHandler):
    async def _create_message(self, *args, **kwargs) -> StreamChunkV2:
        res: StreamChunkV2 = await super()._create_message(*args, **kwargs)
        return res.to_stream_chunk_v1()
