import asyncio
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from functools import lru_cache
from time import perf_counter
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from haystack.dataclasses import StreamingChunk
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from chat2rag.api.schema import Error, Success
from chat2rag.config import CONFIG
from chat2rag.core.database import Prompt, get_db
from chat2rag.core.document.qdrant import QAQdrantDocumentStore
from chat2rag.logger import get_logger
from chat2rag.pipelines.rag import RAGPipeline
from chat2rag.tools.tool_manager import tool_manager
from chat2rag.utils.chat_cache import ChatCache
from chat2rag.utils.monitoring import async_performance_logger
from chat2rag.utils.stream import StreamHandler

logger = get_logger(__name__)
router = APIRouter()
chat_cache = ChatCache()

# 为了避免每次请求都创建新的executor导致资源浪费，使用全局executor
executor = ThreadPoolExecutor(max_workers=5)


class Config:
    """配置常量集中管理"""

    DEFAULT_MODELS = {
        "intention": CONFIG.DEFAULT_INTENTION_MODEL,
        "generator": CONFIG.DEFAULT_GENERATOR_MODEL,
    }

    GENERATION_KWARGS = {
        "temperature": 0.1,
        "presence_penalty": -0.2,
        "max_tokens": 150,
    }


# 使用枚举
class ProcessType(str, Enum):
    BATCH = "batch"
    STREAM = "stream"


class ChatQueryParams(BaseModel):
    """请求参数模型"""

    collection_name: Optional[str] = Field(
        None, alias="collectionName", description="知识库名称"
    )
    query: str = Field(..., description="查询内容")
    top_k: int = Field(default=5, ge=0, le=30, alias="topK", description="返回数量")
    score_threshold: float = Field(
        default=CONFIG.SCORE_THRESHOLD,
        ge=0.0,
        le=1.0,
        alias="scoreThreshold",
        description="文档匹配分数阈值",
    )
    precision_mode: int = Field(
        default=0, alias="precisionMode", description="是否使用精确模式"
    )
    chat_id: Optional[str] = Field(None, alias="chatId", description="聊天的标识")
    chat_rounds: int = Field(
        default=1, ge=0, le=30, alias="chatRounds", description="聊天轮数"
    )
    prompt_name: str = Field("", alias="promptName", description="提示词名称选择")
    intention_model: str = Field(
        default=Config.DEFAULT_MODELS["intention"],
        alias="intentionModel",
        description="意图模型",
    )
    generator_model: str = Field(
        default=Config.DEFAULT_MODELS["generator"],
        alias="generatorModel",
        description="生成模型",
    )
    generation_kwargs: str = Field(
        default="{}",
        alias="generationKwargs",
        description="生成参数",
    )
    tool_list: List[str] = Field(default=[], alias="toolList", description="工具列表")

    class Config:
        populate_by_name = True


@lru_cache(maxsize=32)
def _create_rag_pipeline(*args, **kwargs) -> RAGPipeline:
    """
    Cache rag pipeline
    """
    logger.debug(
        "Creating new rag pipeline for args: %s and kargs: %s", ", ".join(args), kwargs
    )
    return RAGPipeline(*args, **kwargs)


def get_prompt_template(prompt_name: str, db: Session) -> Optional[str]:
    """获取提示词模板"""
    if not prompt_name:
        return None

    try:
        prompt = db.query(Prompt).filter(Prompt.prompt_name == prompt_name).first()
        if not prompt:
            logger.warning("Prompt with name '%s' not found", prompt_name)
            try:
                prompt = (
                    db.query(Prompt)
                    .filter(Prompt.prompt_name in ["默认", "default"])
                    .first()
                )
                return prompt.prompt_text
            except Exception as e:
                logger.error("Error retrieving prompt '%s': %s", prompt_name, str(e))
                return None
        return prompt.prompt_text
    except Exception as e:
        logger.error("Error retrieving prompt '%s': %s", prompt_name, str(e))
        return None


def parse_generation_kwargs(kwargs_str: str) -> dict:
    """解析生成参数"""
    if kwargs_str == "{}" or kwargs_str == "":
        return Config.GENERATION_KWARGS
    try:
        return eval(kwargs_str)
    except Exception as e:
        logger.error("Failed to parse generation_kwargs: %s", str(e))
        return Config.GENERATION_KWARGS


def get_tools(tool_list: List[str]) -> List:
    """获取工具列表"""
    if "all" in tool_list:
        return tool_manager.get_tools()
    return tool_manager.get_tools(tool_list)


@router.get("/query")
@async_performance_logger
async def chat_rag(
    params: ChatQueryParams = Depends(),
    db: Session = Depends(get_db),
):
    logger.info("Processing query request, query: '%s'", params.query)

    # 获取提示词模板
    prompt_template = get_prompt_template(params.prompt_name, db)

    # 使用精准匹配模式，直接索引问题，然后匹配答案
    if params.precision_mode == 1:
        logger.info("Using precision mode for query: '%s'", params.query)
        answer = await QAQdrantDocumentStore(params.collection_name).query_exact(
            params.query
        )
        if answer:
            logger.info(
                "Found exact match for query: '%s'",
                params.query,
            )
            return Success(data=[{"content": answer, "role": "assistant"}])
        logger.info("No exact match found for query: '%s'", params.query)

    # 获取工具和历史消息
    tools = get_tools(params.tool_list)
    logger.debug("Selected %d tools for processing", len(tools))

    history_messages = []
    if params.chat_id:
        history_messages = chat_cache.get_messages(params.chat_id, params.chat_rounds)
        logger.debug(
            "Retrieved %d history messages for chat_id: %s",
            len(history_messages),
            params.chat_id,
        )

    generation_kwargs = parse_generation_kwargs(params.generation_kwargs)

    # 创建并运行RAG管道
    pipeline = _create_rag_pipeline(
        qdrant_index=params.collection_name,
        intention_model=params.intention_model,
        generator_model=params.generator_model,
    )

    logger.debug("Starting RAG pipeline with query: '%s'", params.query)
    response = await pipeline.run(
        query=params.query,
        tools=tools,
        top_k=params.top_k,
        prompt_template=prompt_template,
        score_threshold=params.score_threshold,
        messages=history_messages,
        generation_kwargs=generation_kwargs,
    )

    # 处理返回结果
    chat_list = response.get("generator").get("replies")
    data = []
    for chat_message in chat_list:
        data.append(
            {
                "content": chat_message.text,
                "role": chat_message.role,
                "name": chat_message.name,
                "meta": chat_message.meta,
            }
        )

    # 更新聊天历史
    if params.chat_id and chat_list:
        chat_cache.add_message(params.chat_id, params.query, "user")
        chat_cache.add_message(params.chat_id, chat_list[0].text, "assistant")

    logger.info("Query processed successfully")
    return Success(data=data)


@router.get("/query-stream")
async def chat_rag_stream(
    params: ChatQueryParams = Depends(),
    batch_or_stream: ProcessType = Query(ProcessType.BATCH, alias="batchOrStream"),
    db: Session = Depends(get_db),
):
    start = perf_counter()
    logger.info("Processing streaming query request: '%s'", params.query)

    # 初始化流处理器
    handler = StreamHandler()
    handler.start()

    # 获取参数
    tools = get_tools(params.tool_list)
    is_batch = batch_or_stream == ProcessType.BATCH
    prompt_template = get_prompt_template(params.prompt_name, db)
    generation_kwargs = parse_generation_kwargs(params.generation_kwargs)

    # 获取历史消息
    history_messages = []
    if params.chat_id:
        history_messages = chat_cache.get_messages(params.chat_id, params.chat_rounds)
        logger.debug(
            "Retrieved %d history messages for chat_id: %s",
            len(history_messages),
            params.chat_id,
        )

    # 处理精确模式查询的函数
    async def process_exact_query(answer):
        try:
            logger.debug("Processing exact query match")
            for i in answer:
                meta = {"model": "None", "finish_reason": "none"}
                handler.callback(StreamingChunk(content=i, meta=meta))
                # 重要：添加短暂等待，确保数据流被发送
                await asyncio.sleep(0.01)

            handler.callback(
                StreamingChunk(
                    content="", meta={"model": "None", "finish_reason": "stop"}
                )
            )

            # 更新聊天历史
            if params.chat_id:
                chat_cache.add_message(params.chat_id, params.query, "user")
                chat_cache.add_message(params.chat_id, answer, "assistant")

            logger.info(
                "Exact query processed successfully, took %.2fs", perf_counter() - start
            )
        except Exception as e:
            logger.error("Error in exact query processing: %s", str(e))
        finally:
            handler.finish()

    # 处理RAG管道的函数
    async def process_rag_pipeline():
        try:
            logger.debug("Starting RAG pipeline for streaming response")
            pipeline = _create_rag_pipeline(
                qdrant_index=params.collection_name,
                stream_callback=handler.callback,
                intention_model=params.intention_model,
                generator_model=params.generator_model,
            )

            result = await pipeline.run(
                query=params.query,
                prompt_template=prompt_template,
                tools=tools,
                top_k=params.top_k,
                score_threshold=params.score_threshold,
                messages=history_messages,
                generation_kwargs=generation_kwargs,
            )

            # 更新聊天历史
            if (
                params.chat_id
                and "generator" in result
                and "replies" in result["generator"]
                and result["generator"]["replies"]
            ):
                chat_cache.add_message(params.chat_id, params.query, "user")
                chat_cache.add_message(
                    params.chat_id, result["generator"]["replies"][0].text, "assistant"
                )

            logger.info(
                "RAG pipeline completed successfully, took %.2fs",
                perf_counter() - start,
            )
        except Exception as e:
            logger.error("Error in RAG pipeline: %s", str(e))
            # 发送错误信息到流
            handler.callback(
                StreamingChunk(
                    content=f"处理请求时发生错误: {str(e)}",
                    meta={"model": "error", "finish_reason": "error"},
                )
            )
        finally:
            # 确保流被正确关闭
            handler.finish()

    # 使用精准匹配模式，直接索引问题，然后匹配答案
    if params.precision_mode == 1:
        logger.info("Using precision mode for streaming query")
        answer = await QAQdrantDocumentStore(params.collection_name).query_exact(
            params.query
        )
        if answer:
            logger.info("Found exact match for query: '%s'", params.query)
            # 创建一个不依赖于当前事件循环的任务
            asyncio.create_task(process_exact_query(answer))

            return StreamingResponse(
                handler.get_stream(is_batch),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Transfer-Encoding": "chunked",
                },
            )
        logger.info(
            "No exact match found for query: '%s', falling back to RAG", params.query
        )

    # 关键修改：使用独立线程运行事件循环
    def run_async_in_thread(coro):
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    # 提交任务到线程池
    executor.submit(run_async_in_thread, process_rag_pipeline())

    # 返回流式响应
    return StreamingResponse(
        handler.get_stream(is_batch),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Transfer-Encoding": "chunked",
        },
    )
