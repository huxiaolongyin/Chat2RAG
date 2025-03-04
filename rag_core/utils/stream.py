import copy
import datetime
import json
import uuid
from dataclasses import dataclass
from queue import Queue
from time import perf_counter
from typing import List, Optional

from haystack.dataclasses import StreamingChunk

from rag_core.logging import logger


@dataclass
class StreamConfig:
    """流式配置"""

    # 中文标点
    CN_SYMBOLS = ["，", "；", "。", "：", "？", "！", "\n"]
    # 英文标点
    EN_SYMBOLS = [",", ";", "?", "!"]

    # 批量大小
    batch_size: int = 50
    # 分隔符号
    split_symbols: List[str] = None

    def __post_init__(self):
        if self.split_symbols is None:
            self.split_symbols = self.CN_SYMBOLS + self.EN_SYMBOLS


class StreamHandler:
    def __init__(self, config: Optional[StreamConfig] = None):
        self.stream_start = perf_counter()
        self.queue = Queue()
        self.config = config or StreamConfig()
        self.doc_length = 0  # 新增属性

    def callback(self, chunk: StreamingChunk):
        self.queue.put(chunk)

    def set_doc_info(self, doc_count: int):
        self.queue.put({"type": "doc_info", "count": doc_count})

    def _create_message(
        self,
        content: str,
        meta: dict = None,
        is_start: int = 0,
        message_id: str = None,
    ) -> dict:
        """创建消息格式"""
        if meta is None:
            meta = {"model": "None", "finish_reason": "none"}
        if meta["finish_reason"] == "stop":
            status = 2
        elif is_start:
            status = 0
        else:
            status = 1

        return {
            "object": "message",
            "content": content,
            "model": meta["model"],
            "status": status,
            "documentCount": self.doc_length,
            "createTime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "messageId": message_id,
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

    def get_stream(self, is_batch: bool = False):
        first_response = True  # 添加标志位跟踪第一条响应
        message_id = str(uuid.uuid4().hex[:16])
        if not is_batch:

            # 流式处理模式
            while True:
                chunk = self.queue.get()

                if isinstance(chunk, dict) and chunk.get("type") == "doc_info":
                    self.doc_length = chunk["count"]
                    continue
                if chunk == "[START]":
                    # 开始处理新一批数据
                    data = self._create_message("", is_start=1, message_id=message_id)
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                    continue

                if chunk == "[END]":
                    break

                if first_response:
                    elapsed = perf_counter() - self.stream_start
                    logger.info(f"RAG pipeline query response time: {elapsed:.3f}s")
                    first_response = False

                data = self._create_message(
                    chunk.content, chunk.meta, message_id=message_id
                )
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
        else:
            # 批量处理模式
            current_batch = []
            while True:
                chunk = self.queue.get()

                if isinstance(chunk, dict) and chunk.get("type") == "doc_info":
                    self.doc_length = chunk["count"]
                    continue

                if chunk == "[START]":
                    # 开始处理新一批数据
                    data = self._create_message("", is_start=1, message_id=message_id)
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                    continue

                if chunk == "[END]":
                    # 处理最后一批数据
                    if current_batch:
                        combined_content = "".join([c.content for c in current_batch])
                        data = self._create_message(
                            combined_content,
                            current_batch[-1].meta,
                            message_id=message_id,
                        )
                        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                    break

                # 检查当前chunk的内容是否包含需要分割的符号
                content = chunk.content
                last_split_pos = 0

                for i, char in enumerate(content):
                    if self._is_split_punctuation(
                        char
                    ):  # 新增辅助函数判断是否是需要分割的符号
                        # 发现符号，准备分割并输出
                        # 先将chunk分割点之前的内容加入current_batch
                        split_chunk = copy.copy(chunk)
                        split_chunk.content = content[
                            last_split_pos : i + 1
                        ]  # 包含符号本身
                        current_batch.append(split_chunk)

                        # 生成当前批次的内容
                        batch_content = "".join([c.content for c in current_batch])

                        if first_response:
                            elapsed = perf_counter() - self.stream_start
                            logger.info(
                                f"RAG pipeline query response time: {elapsed:.3f}s"
                            )
                            first_response = False

                        # 输出当前批次
                        data = self._create_message(
                            batch_content, chunk.meta, message_id=message_id
                        )
                        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

                        # 重置批次
                        current_batch = []
                        last_split_pos = i + 1

                # 处理剩余未分割的内容
                if last_split_pos < len(content):
                    remaining_chunk = copy.copy(chunk)
                    remaining_chunk.content = content[last_split_pos:]
                    current_batch.append(remaining_chunk)

    def start(self):
        self.queue.put("[START]")

    def finish(self):
        self.queue.put("[END]")
