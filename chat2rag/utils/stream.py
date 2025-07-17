import copy
import datetime
import json
import uuid
from queue import Queue
from time import perf_counter
from typing import Optional

from haystack.dataclasses import StreamingChunk

from chat2rag.dataclass.stream import StreamConfig
from chat2rag.logger import get_logger

logger = get_logger(__name__)


class StreamHandler:
    def __init__(self, config: Optional[StreamConfig] = None):
        self.stream_start = perf_counter()
        self.queue = Queue()
        self.model = None
        self.config = config or StreamConfig()
        self.doc_length = 0
        self.message_id = str(uuid.uuid4().hex[:16])

    def callback(self, chunk: StreamingChunk):
        self.queue.put(chunk)

    def set_doc_info(self, doc_count: int):
        self.queue.put({"type": "doc_info", "count": doc_count})

    def _create_message(
        self,
        content: str,
        meta: dict = None,
        tool: str = None,
        arguments: dict = {},
        tool_result: dict = {},
        is_start: int = 0,
    ) -> dict:
        """创建消息格式"""
        if meta is None:
            meta = {"model": "None", "finish_reason": "none"}
        if meta.get("finish_reason") == "stop":
            status = 2
        elif is_start:
            status = 0
        else:
            status = 1

        return {
            "object": "message",
            "content": content,
            "model": self.model,
            "status": status,
            "tool": tool,
            "arguments": arguments,
            "toolResult": tool_result,
            "documentCount": self.doc_length,
            "createTime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "messageId": self.message_id,
        }

    def _should_flush_batch(self, chunk: str, batch_content: str) -> bool:
        """判断是否需要输出当前批次"""
        return (
            chunk.content in self.config.split_symbols
            or chunk.content.rstrip() in self.config.split_symbols
            or len(batch_content) >= self.config.batch_size
        )

    def _is_split_punctuation(self, char):
        # 定义需要在何处分割的符号，包括中文标点和英文标点
        return char in self.config.split_symbols

    def __handle_first_response(self):
        """处理首次响应，记录时间指标"""
        elapsed = perf_counter() - self.stream_start
        logger.info(f"RAG pipeline query response time: {elapsed:.3f}s")
        return False

    def __yield_data(self, content="", meta=None, **kwargs):
        """生成并发送数据"""
        data = self._create_message(content, meta, **kwargs)
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    def __handle_tool_call(self, chunk):
        """处理工具调用信息"""
        tool_call = chunk.meta.get("tool_call", {})
        tool_result = chunk.meta.get("tool_result", {})
        tool_name = ""
        arguments = {}

        if tool_call:
            tool_name = tool_call.tool_name
            arguments = tool_call.arguments

        if tool_result:
            try:
                tool_result = json.loads(str(tool_result))
                tool_result.get("content")[0]["text"] = json.loads(
                    tool_result.get("content")[0]["text"]
                )

            except Exception:
                logger.warning("解析工具调用结果失败，使用原始结果")

        yield self.__yield_data(
            "", chunk.meta, tool=tool_name, arguments=arguments, tool_result=tool_result
        )

    def get_stream(self, is_batch: bool = False):
        first_response = True  # 添加标志位跟踪第一条响应
        current_batch = []

        while True:
            chunk = self.queue.get()

            # 处理特殊控制消息
            if isinstance(chunk, dict) and chunk.get("type") == "doc_info":
                self.doc_length = chunk["count"]
                continue

            if chunk == "[START]":
                yield self.__yield_data("", is_start=1)
                continue

            if chunk == "[END]":
                # 批处理模式下，处理最后一批数据
                if is_batch and current_batch:
                    combined_content = "".join([c.content for c in current_batch])
                    yield self.__yield_data(combined_content, current_batch[-1].meta)

                # 发送结束消息
                if is_batch:
                    yield self.__yield_data(
                        "", meta={"finish_reason": "stop", "model": ""}
                    )
                break

            if not self.model:
                self.model = chunk.meta.get("model", "")

            if chunk.meta.get("tool_call") or chunk.meta.get("tool_result"):
                for item in self.__handle_tool_call(chunk):
                    yield item
                continue

            # 处理内容
            if not is_batch:
                # 单条流式处理模式
                if first_response:
                    first_response = self.__handle_first_response()
                if chunk.content or chunk.meta.get("finish_reason") == "stop":
                    yield self.__yield_data(chunk.content, chunk.meta)
            else:
                # 批处理模式
                content = chunk.content
                last_split_pos = 0

                # 遍历内容，查找分割点
                for i, char in enumerate(content):
                    if self._is_split_punctuation(char):
                        # 将分割点前的内容加入当前批次
                        split_chunk = copy.copy(chunk)
                        split_chunk.content = content[
                            last_split_pos : i + 1
                        ]  # 包含分隔符
                        current_batch.append(split_chunk)

                        # 合并并发送当前批次
                        batch_content = "".join([c.content for c in current_batch])
                        if first_response:
                            first_response = self.__handle_first_response()
                        yield self.__yield_data(batch_content, chunk.meta)

                        # 重置批次
                        current_batch = []
                        last_split_pos = i + 1

                # 处理剩余内容
                if last_split_pos < len(content):
                    remaining_chunk = copy.copy(chunk)
                    remaining_chunk.content = content[last_split_pos:]
                    current_batch.append(remaining_chunk)

    def start(self):
        self.queue.put("[START]")

    def finish(self):
        self.queue.put("[END]")
