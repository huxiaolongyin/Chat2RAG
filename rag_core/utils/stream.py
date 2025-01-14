import datetime
import json
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
        self, content: str, meta: dict = None, is_start: int = 0
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
        }

    def _should_flush_batch(self, chunk: str, batch_content: str) -> bool:
        """判断是否需要输出当前批次"""
        return (
            chunk.content in self.config.split_symbols
            or chunk.content.rstrip() in self.config.split_symbols
            or len(batch_content) >= self.config.batch_size
        )

    def get_stream(self, is_batch: bool = False):
        first_response = True  # 添加标志位跟踪第一条响应
        if not is_batch:

            # 流式处理模式
            while True:
                chunk = self.queue.get()
                if isinstance(chunk, dict) and chunk.get("type") == "doc_info":
                    self.doc_length = chunk["count"]
                    continue
                if chunk == "[START]":
                    # 开始处理新一批数据
                    data = self._create_message("", is_start=1)
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                    continue

                if chunk == "[END]":
                    break

                if first_response:
                    elapsed = perf_counter() - self.stream_start
                    logger.info(f"RAG pipeline query response time: {elapsed:.3f}s")
                    first_response = False

                data = self._create_message(chunk.content, chunk.meta)
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
                    data = self._create_message("", is_start=1)
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                    continue
                if chunk == "[END]":
                    # 处理最后一批数据
                    if current_batch:
                        combined_content = "".join([c.content for c in current_batch])
                        data = self._create_message(
                            combined_content, current_batch[-1].meta
                        )
                        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                    break

                current_batch.append(chunk)

                batch_content = "".join([c.content for c in current_batch])
                if self._should_flush_batch(chunk, batch_content):
                    if first_response:
                        elapsed = perf_counter() - self.stream_start
                        logger.info(f"RAG pipeline query response time: {elapsed:.3f}s")
                        first_response = False

                    data = self._create_message(batch_content, chunk.meta)
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                    current_batch = []

    def start(self):
        self.queue.put("[START]")

    def finish(self):
        self.queue.put("[END]")
