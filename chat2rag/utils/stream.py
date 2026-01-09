import asyncio
import copy
import datetime
import json
import re
import uuid
from time import perf_counter
from typing import Optional

from haystack.dataclasses import StreamingChunk

from chat2rag.dataclass.stream import StreamConfig
from chat2rag.logger import get_logger
from chat2rag.schemas.chat import (
    BehaviorSchema,
    ContentSchema,
    StreamChunkV2,
    ToolSchema,
)
from chat2rag.services.action_service import RobotActionService
from chat2rag.services.expression_service import RobotExpressionService
from chat2rag.services.metric_service import MetricCreate, MetricService

logger = get_logger(__name__)
expression_service = RobotExpressionService()
action_service = RobotActionService()


class StreamHandler:
    def __init__(self, config: Optional[StreamConfig] = None):
        self.stream_start = perf_counter()
        self.queue = asyncio.Queue()
        self.model = None
        self.config = config or StreamConfig()
        self.doc_length = 0
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
            "extra_params": {},
            "retrieval_params": {},
            "execute_tools": "",
            "meta_data": {},
        }

        # 初始化指标服务
        self.metric_service = MetricService()

    async def callback(self, chunk: StreamingChunk):
        await self.queue.put(chunk)

    async def set_doc_info(self, doc_count: int):
        await self.queue.put({"type": "doc_info", "count": doc_count})
        self.metrics["document_count"] = doc_count

    def set_query_info(
        self,
        question: str,
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
        """设置查询信息"""
        # 问题
        self.metrics["question"] = question

        # 会话信息
        self.metrics["chat_id"] = chat_id
        self.metrics["chat_rounds"] = chat_rounds

        # 知识库
        if isinstance(collections, list):
            collections = ",".join(collections)
        if collections:
            self.metrics["collections"] = collections
        self.metrics["retrieval_params"] = retrieval_params

        # 模型
        if model:
            self.metrics["model"] = model
            self.model = model

        # 提示词
        if prompt:
            self.metrics["prompt"] = prompt

        # 精准模式
        self.metrics["precision_mode"] = precision_mode

        # 工具
        self.metrics["tools"] = ",".join(tools)

        # 额外参数
        self.metrics["extra_params"] = extra_params

    def set_tool_info(self, tools: str = None):
        """设置执行工具信息"""
        if tools:
            if self.metrics.get("execute_tools"):
                self.metrics["execute_tools"] += "," + tools
            else:
                self.metrics["execute_tools"] = tools

            # TODO: 临时措施
            self.metrics["tool_ms"] = round((perf_counter() - self.stream_start) * 1000, 2)

    def set_token_info(self, input_tokens: int = 0, output_tokens: int = 0):
        """设置Token信息"""
        self.metrics["input_tokens"] += input_tokens
        self.metrics["output_tokens"] += output_tokens

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

    async def _parse_behavior_tags(self, text: str):
        """
        Extract behavioral labels from the text and return the cleaned text
        TODO: 处理流式返回
        """
        emojis = re.findall(r"\[EMOJI:(.*?)\]", text)
        actions = re.findall(r"\[ACTION:(.*?)\]", text)
        links = re.findall(r"\[LINK:(.*?)\]", text)
        images = re.findall(r"\[IMAGE:(.*?)\]", text)

        # 移除所有标记，保留纯文本
        clean_text = re.sub(r"\[(EMOJI|ACTION|LINK|IMAGE):.*?\]", "", text).strip()
        emoji_code = await expression_service.get_code_by_name(next(iter(emojis), ""))
        action_code = await action_service.get_code_by_name(next(iter(actions), ""))

        return {
            "emoji": emoji_code,
            "action": action_code,
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
        """创建消息格式"""
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

        # 解析行为标签
        behavior_data = (
            await self._parse_behavior_tags(content)
            if content
            else {"clean_text": "", "emoji": "", "action": "", "link": "", "image": ""}
        )
        clean_content = behavior_data["clean_text"]

        # 累积回答内容 TODO 优化
        if content:
            self.metrics["answer"] += clean_content

        if tool:
            tool_content = ToolSchema(tool_name=tool, tool_type=tool_type, arguments=arguments, tool_result=tool_result)
            # {
            #     "toolName": tool,
            #     "toolType": tool_type,
            #     "arguments": arguments,
            #     "toolResult": tool_result,
            # }

        else:
            tool_content = {}
        return StreamChunkV2(
            input=query,
            content=ContentSchema(text=behavior_data["clean_text"], image=behavior_data["image"]),
            model=self.model,
            status=status,
            behavior=BehaviorSchema(emoji=behavior_data["emoji"], action=behavior_data["action"]),
            tool=tool_content,
            link=behavior_data["link"],
            document_count=self.doc_length,
            message_id=self.message_id,
        )

    # {
    #         "object": "message",
    #         "input": query,
    #         "content": {
    #             "text": behavior_data["clean_text"],
    #             "image": behavior_data["image"],
    #         },
    #         "model": self.model,
    #         "status": status,
    #         "behavior": {
    #             "emoji": behavior_data["emoji"],
    #             "action": behavior_data["action"],
    #         },
    #         "tool": tool_content,
    #         "link": behavior_data["link"],
    #         "documentCount": self.doc_length,
    #         "createTime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    #         "messageId": self.message_id,
    #     }

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

    async def __yield_data(self, content="", meta=None, **kwargs):
        """生成并发送数据"""
        data = await self._create_message(content, meta, **kwargs)
        yield f"data: {json.dumps(data.model_dump(by_alias=True), ensure_ascii=False)}\n\n"

    async def __handle_tool_call(self, chunk):
        """处理工具调用信息"""
        tool_call = chunk.meta.get("tool_call", {})
        tool_result = chunk.meta.get("tool_result", {})
        tool_name = ""
        arguments = {}

        if tool_call:
            tool_name = tool_call.tool_name
            arguments = tool_call.arguments

            # 记录工具调用信息
            self.set_tool_info(tool_name)

        if tool_result:
            try:
                tool_result = json.loads(str(tool_result))
                tool_result.get("content")[0]["text"] = json.loads(tool_result.get("content")[0]["text"])
                tool_result["content"] = tool_result.get("content")[0]

            except Exception:
                logger.warning("The call result of the json parsing tool failed. Use the original result")

            # 记录工具结果
            self.metrics["tool_result"] = tool_result if isinstance(tool_result, dict) else {}

        # yield self.__yield_data(
        #     "", chunk.meta, tool=tool_name, arguments=arguments, tool_result=tool_result
        # )
        async for data_str in self.__yield_data(
            "", chunk.meta, tool=tool_name, arguments=arguments, tool_result=tool_result
        ):
            yield data_str

    async def get_stream(self, is_batch: bool = False, query: dict = {}):
        first_response = True  # 添加标志位跟踪第一条响应
        current_batch = []

        while True:
            chunk = await self.queue.get()

            # 处理特殊控制消息
            if isinstance(chunk, dict) and chunk.get("type") == "doc_info":
                self.doc_length = chunk["count"]
                continue

            if chunk == "[START]":
                async for data_str in self.__yield_data("", is_start=1, query=query):
                    yield data_str
                continue

            if chunk == "[END]":
                # 批处理模式下，处理最后一批数据
                if is_batch and current_batch:
                    combined_content = "".join([c.content for c in current_batch])
                    # yield self.__yield_data(combined_content, current_batch[-1].meta)
                    async for data_str in self.__yield_data(combined_content, current_batch[-1].meta):
                        yield data_str

                # 发送结束消息
                if is_batch:
                    async for data_str in self.__yield_data("", meta={"finish_reason": "stop", "model": ""}):
                        yield data_str
                    # yield self.__yield_data(
                    #     "", meta={"finish_reason": "stop", "model": ""}
                    # )
                # 保存指标
                await self.save_metrics()
                break

            if not self.model:
                self.model = chunk.meta.get("model", "")
                self.metrics["model"] = self.model

            if chunk.meta.get("tool_call") or chunk.meta.get("tool_result"):
                async for item in self.__handle_tool_call(chunk):
                    yield item
                continue

            # 处理内容
            if not is_batch:
                # 单条流式处理模式
                if first_response:
                    first_response = self.__handle_first_response()
                    # yield self.__yield_data(chunk.content, chunk.meta)
                    async for data_str in self.__yield_data(chunk.content, chunk.meta):
                        yield data_str
                    continue
                if chunk.content or chunk.meta.get("finish_reason") == "stop":
                    async for data_str in self.__yield_data(chunk.content, chunk.meta):
                        yield data_str
                    # yield self.__yield_data(chunk.content, chunk.meta)
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
                        # yield self.__yield_data(batch_content, chunk.meta)
                        async for data_str in self.__yield_data(batch_content, chunk.meta):
                            yield data_str

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
