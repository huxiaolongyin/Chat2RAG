import asyncio
import copy
import datetime
import json
import re
import uuid
from dataclasses import dataclass
from time import perf_counter
from typing import List, Optional

from haystack.dataclasses import StreamingChunk

from chat2rag.logger import logger
from chat2rag.schemas.chat import StreamChunkV1
from chat2rag.services.metric_service import MetricCreate, MetricService


@dataclass
class StreamConfig:
    """流式配置"""

    # 中文标点
    CN_SYMBOLS = ["，", "；", "。", "：", "？", "！", "\n", "、"]
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
        self.queue = asyncio.Queue()
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

    async def callback(self, chunk: StreamingChunk):
        await self.queue.put(chunk)

    async def set_doc_info(self, doc_count: int):
        await self.queue.put({"type": "doc_info", "count": doc_count})
        self.metrics["document_count"] = doc_count

    def set_chat_info(self, chat_id: str, chat_rounds: int = None):
        """设置会话信息"""
        self.metrics["chat_id"] = chat_id
        self.metrics["chat_rounds"] = chat_rounds

    def set_query_info(
        self,
        question: str,
        model: str = None,
        prompt: str = None,
        precision_mode: bool = False,
    ):
        """设置查询信息"""
        self.metrics["question"] = question
        if model:
            self.metrics["model"] = model
        if prompt:
            self.metrics["prompt"] = prompt
        self.metrics["precision_mode"] = precision_mode

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

    async def save_metrics(self):
        """保存指标到数据库"""
        try:
            # 计算总响应时间
            total_time = perf_counter() - self.stream_start
            self.metrics["total_ms"] = round(total_time * 1000, 2)

            # 创建指标记录
            metric_data = MetricCreate(**self.metrics)
            await self.metric_service.create(metric_data)
            logger.info(f"Performance metrics saved for message {self.message_id}")

        except Exception as e:
            logger.error(f"Failed to save metrics: {str(e)}")

    def _create_message(
        self,
        content: str,
        meta: dict = None,
        is_start: int = 0,
        message_id: str = None,
    ) -> StreamChunkV1:
        """创建消息格式"""
        if meta is None:
            meta = {"model": "None", "finish_reason": "none"}
        if meta["finish_reason"] == "stop":
            status = 2
        elif is_start:
            status = 0
        else:
            status = 1

        parse_content = ""
        if content:
            parse_content = re.sub(r"\[(EMOJI|ACTION|LINK|IMAGE):.*?\]", "", content).strip()
            self.metrics["answer"] += parse_content

        return StreamChunkV1(
            content=parse_content,
            model=meta["model"],
            status=status,
            document_count=self.doc_length,
            message_id=message_id,
        )

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
        self.metrics["first_response_ms"] = round(elapsed * 1000, 2)
        logger.info(f"The first reply time of the Agent pipeline. Cost: {elapsed:.3f}s")
        return False

    def __yield_data(self, content="", meta=None, **kwargs):
        """生成并发送数据"""
        data = self._create_message(content, meta, **kwargs)
        return f"data: {json.dumps(data.model_dump(by_alias=True), ensure_ascii=False)}\n\n"

    async def get_stream(self, is_batch: bool = False, **kwargs):
        first_response = True  # 添加标志位跟踪第一条响应
        message_id = str(uuid.uuid4().hex[:16])
        current_batch = []

        while True:
            chunk = await self.queue.get()

            # 处理特殊控制消息
            if isinstance(chunk, dict) and chunk.get("type") == "doc_info":
                self.doc_length = chunk["count"]
                continue

            if chunk == "[START]":
                yield self.__yield_data("", is_start=1, message_id=message_id)
                continue

            if chunk == "[END]":
                # 处理最后一批数据
                if is_batch and current_batch:
                    combined_content = "".join([c.content for c in current_batch])

                    yield self.__yield_data(
                        combined_content,
                        current_batch[-1].meta,
                        message_id=message_id,
                    )

                if is_batch:
                    yield self.__yield_data(
                        "",
                        meta={"finish_reason": "stop", "model": ""},
                        message_id=message_id,
                    )
                # 保存指标
                await self.save_metrics()
                break

            # 处理内容
            if not is_batch:
                # 单条流式处理模式
                if first_response:
                    first_response = self.__handle_first_response()
                    yield self.__yield_data(chunk.content, chunk.meta, message_id=message_id)
                    continue
                if chunk.content or chunk.meta.get("finish_reason") == "stop":
                    yield self.__yield_data(chunk.content, chunk.meta, message_id=message_id)
            else:
                # 批处理模式
                content = chunk.content
                last_split_pos = 0

                # 遍历内容，查找分割点
                for i, char in enumerate(content):
                    if self._is_split_punctuation(char):
                        # 将分割点前的内容加入当前批次
                        split_chunk = copy.copy(chunk)
                        split_chunk.content = content[last_split_pos : i + 1]  # 包含分隔符
                        current_batch.append(split_chunk)

                        # 合并并发送当前批次
                        batch_content = "".join([c.content for c in current_batch])
                        if first_response:
                            first_response = self.__handle_first_response()
                        yield self.__yield_data(batch_content, chunk.meta, message_id=message_id)

                        # 重置批次
                        current_batch = []
                        last_split_pos = i + 1

                # 处理剩余内容
                if last_split_pos < len(content):
                    remaining_chunk = copy.copy(chunk)
                    remaining_chunk.content = content[last_split_pos:]
                    current_batch.append(remaining_chunk)

    async def start(self):
        await self.queue.put("[START]")

    async def finish(self):
        await self.queue.put("[END]")
