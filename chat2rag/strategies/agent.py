import asyncio
import os
import re
from datetime import datetime
from time import perf_counter
from typing import AsyncIterator, List

from haystack.dataclasses import ChatMessage, ChatRole, StreamingChunk

from chat2rag.config import CONFIG
from chat2rag.core.logger import get_logger
from chat2rag.models.models import ModelProvider, ModelSource
from chat2rag.pipelines.agent import AgentPipeline
from chat2rag.services.model_service import model_source_service
from chat2rag.utils.chat_history import chat_history
from chat2rag.utils.merge_kwargs import merge_generation_kwargs
from chat2rag.utils.pipeline_cache import create_pipeline

from .base import ResponseStrategy

logger = get_logger(__name__)


class AgentStrategy(ResponseStrategy):
    """Agent 兜底策略"""

    async def can_handle(self, query: str) -> bool:
        # Agent 作为兜底策略，总是可以处理
        return True

    async def execute(self, query: str) -> AsyncIterator[str]:
        history_messages = await chat_history.get_history_messages(
            self.request.prompt_name,
            self.request.chat_id,
            self.request.chat_rounds,
            image=self.request.content.image,
        )
        # 保存任务引用
        task = asyncio.create_task(self._process_pipeline(query, history_messages))

        try:
            async for chunk in self.handler.get_stream(self.is_batch):
                yield chunk
        finally:
            # 确保后台任务完成
            await task

    async def _process_pipeline(self, query: str, history_messages: List[ChatMessage]):
        """处理 Agent Pipeline"""

        # 获取当前时间
        current_time = {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        model_source: ModelSource = await model_source_service.get_best_source(
            self.request.model, extra_log="Agent Stage"
        )
        model_provider: ModelProvider = await model_source.provider
        generation_kwargs = merge_generation_kwargs(
            self.request.generation_kwargs,
            model_source.generation_kwargs,
            CONFIG.GENERATION_KWARGS,
        )
        try:
            pipeline = await create_pipeline(
                AgentPipeline,
                collections=self.request.collections,
                model=model_source.name,
                tools=self.request.tools,
                api_base_url=model_provider.base_url,
                api_key=model_provider.api_key,
                generation_kwargs=generation_kwargs,
            )

            tool_sources = pipeline.get_tool_sources()
            self.handler.set_tool_sources(tool_sources)

            result = await pipeline.run(
                query=query,
                top_k=self.request.top_k,
                score_threshold=self.request.score_threshold,
                filters={
                    "field": "meta.doc_type",
                    "operator": "==",
                    "value": "qa_pair",
                },
                messages=history_messages,
                extra_params=self.request.extra_params | current_time,
                streaming_callback=self.handler.callback,
            )

            documents = result.get("doc_joiner", {}).get("documents", [])
            doc_sources = self._extract_sources(documents)
            if doc_sources and not self.handler._execute_tools_list:
                self.handler.set_source(", ".join(doc_sources))
            elif not self.handler._execute_tools_list:
                self.handler.set_source("大模型生成")

            # 更新聊天历史
            messages: list = result.get("agent", {}).get("messages", [])
            new_messages = self._get_latest_user_round(messages)
            if self.request.chat_id and messages:
                chat_history.add_message(self.request.chat_id, messages=new_messages)
                elapsed_time = perf_counter() - self.start_time
                logger.info(f"Agent pipeline completed in {elapsed_time:.2f}s")
                logger.debug(f"Answer: {new_messages[-1].text}")

            # 更新 token 消费
            input_tokens = 0
            output_tokens = 0
            for message in new_messages:
                if message.role == ChatRole.ASSISTANT:
                    usage = message.meta.get("usage", {})
                    if usage:
                        input_tokens += int(usage.get("prompt_tokens", 0))
                        output_tokens += int(usage.get("completion_tokens", 0))
            self.handler.set_token_info(input_tokens, output_tokens)

        except Exception as e:
            logger.exception("Failed to execute agent strategy")
            self.handler.set_error(str(e))
            await self.handler.callback(
                StreamingChunk(
                    content="交互发生了一点小问题，等待工程师爸爸修复",
                    meta={"model": "error", "finish_reason": "error"},
                )
            )
        finally:
            await self.handler.finish()

    @staticmethod
    def _get_latest_user_round(messages: List[ChatMessage]) -> List[ChatMessage]:
        """获取最新一轮对话"""
        if not messages:
            return []

        # 从后往前找最后一个 user 消息的位置
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].role == "user":
                return messages[i:]

        return []

    def _extract_sources(self, documents: list) -> List[str]:
        """从文档中提取来源信息"""
        sources = []
        seen = set()
        for doc in documents:
            meta = getattr(doc, "meta", {}) or {}
            source_info = meta.get("source", {})
            file_path = (
                source_info.get("file_path", "")
                if isinstance(source_info, dict)
                else ""
            )

            # 从文档 meta 中获取知识库名称
            collection = meta.get("collection_name", "")

            # 清理文件名：去除文件夹路径和时间戳
            if file_path:
                # 获取文件名（去除路径）
                file_name = os.path.basename(file_path)
                # 去除时间戳后缀（格式：_数字）
                file_name = re.sub(r"_\d+(\.[^.]+)$", r"\1", file_name)
            else:
                file_name = ""

            # 构建来源字符串
            if collection and file_name:
                source_str = f"{collection}-{file_name}"
            elif collection:
                source_str = collection
            elif file_name:
                source_str = file_name
            else:
                continue

            if source_str not in seen:
                seen.add(source_str)
                sources.append(source_str)

        return sources
