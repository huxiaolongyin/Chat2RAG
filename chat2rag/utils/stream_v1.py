import datetime
import json
import uuid
from dataclasses import dataclass
from queue import Queue
from time import perf_counter
from typing import List, Optional

from haystack.dataclasses import StreamingChunk

from chat2rag.database.connection import db_session
from chat2rag.database.services.metric_service import MetricCreate, MetricService
from chat2rag.logger import logger


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


class StreamHandlerV1:
    def __init__(self, config: Optional[StreamConfig] = None):
        self.stream_start = perf_counter()
        self.queue = Queue()
        self.model = None
        self.config = config or StreamConfig()
        self.doc_length = 0  # 新增属性
        self.message_id = str(uuid.uuid4().hex[:16])

        # 初始化性能指标字典
        self.metrics = {
            "message_id": self.message_id,
            "create_time": datetime.datetime.now(),
            "chat_id": None,
            "chat_rounds": None,
            "question": "",
            "answer": "",
            "model": "",
            "prompt": None,
            "tools": "",
            "collections": None,
            "document_count": 0,
            "document_ms": 0.0,
            "tool_ms": 0.0,
            "first_response_ms": None,
            "total_ms": None,
            "input_tokens": 0,
            "output_tokens": 0,
            "tool_result": {},
            "error_message": None,
            "precision_mode": False,
            "meta_data": {},
        }

        # 初始化指标服务
        self.metric_service = MetricService()

    def callback(self, chunk: StreamingChunk):
        self.queue.put(chunk)

    def set_doc_info(self, doc_count: int):
        self.queue.put({"type": "doc_info", "count": doc_count})
        self.metrics["document_count"] = doc_count

    def set_chat_info(self, chat_id: str, chat_rounds: int = None):
        """设置会话信息"""
        self.metrics["chat_id"] = chat_id
        self.metrics["chat_rounds"] = chat_rounds

    def set_query_info(self, question: str, model: str = None, prompt: str = None):
        """设置查询信息"""
        self.metrics["question"] = question
        if model:
            self.metrics["model"] = model
        if prompt:
            self.metrics["prompt"] = prompt

    def set_tool_info(self, tools: str = None, tool_time_ms: float = 0.0):
        """设置工具信息"""
        if tools:
            self.metrics["tools"] = tools
        self.metrics["tool_ms"] = tool_time_ms

    def set_collection_info(self, collections: str | list = None):
        """设置知识库信息"""
        if isinstance(collections, list):
            collections = ",".join(collections)
        if collections:
            self.metrics["collections"] = collections

    def set_token_info(self, input_tokens: int = 0, output_tokens: int = 0):
        """设置Token信息"""
        self.metrics["input_tokens"] = input_tokens
        self.metrics["output_tokens"] = output_tokens

    def set_error(self, error_message: str):
        """设置错误信息"""
        self.metrics["error_message"] = error_message

    def save_metrics(self):
        """保存指标到数据库"""
        try:
            # 计算总响应时间
            total_time = perf_counter() - self.stream_start
            self.metrics["total_ms"] = round(total_time * 1000, 2)

            try:
                with db_session() as db:
                    # 创建指标记录
                    metric_data = MetricCreate(**self.metrics)
                self.metric_service.create_metric(db, metric_data)
                logger.info(f"Performance metrics saved for message {self.message_id}")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to save metrics: {str(e)}")

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

        if content:
            self.metrics["answer"] += content

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
                    logger.info(
                        f"The first reply time of the RAG pipeline. Cost: {elapsed:.3f}s"
                    )
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

                    # 保存指标
                    self.save_metrics()
                    break

                if not self.model:
                    self.model = chunk.meta.get("model", "")
                    self.metrics["model"] = self.model

                current_batch.append(chunk)

                batch_content = "".join([c.content for c in current_batch])
                if self._should_flush_batch(chunk, batch_content):
                    if first_response:
                        elapsed = perf_counter() - self.stream_start
                        self.metrics["first_response_ms"] = round(elapsed * 1000, 2)
                        logger.info(
                            f"The first reply time of the RAG pipeline. Cost:{elapsed:.3f}s"
                        )
                        first_response = False

                    data = self._create_message(
                        batch_content, chunk.meta, message_id=message_id
                    )
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                    current_batch = []

    def start(self):
        self.queue.put("[START]")

    def finish(self):
        self.queue.put("[END]")
