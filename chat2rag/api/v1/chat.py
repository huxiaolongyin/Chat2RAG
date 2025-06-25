import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

# from functools import lru_cache
from time import perf_counter
from typing import List, Optional, Union

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from haystack.dataclasses import StreamingChunk
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from chat2rag.api.schema import Error, Success
from chat2rag.config import CONFIG
from chat2rag.core.database import Prompt, get_db
from chat2rag.core.document.qdrant import QAQdrantDocumentStore
from chat2rag.logger import get_logger
from chat2rag.pipelines.rag import RAGPipeline
from chat2rag.utils.chat_cache import ChatCache
from chat2rag.utils.monitoring import async_performance_logger
from chat2rag.utils.stream import StreamHandler

logger = get_logger(__name__)
router = APIRouter()
chat_cache = ChatCache()

# 为了避免每次请求都创建新的executor导致资源浪费，使用全局executor
executor = ThreadPoolExecutor(max_workers=5)


# 使用枚举
class ProcessType(str, Enum):
    BATCH = "batch"
    STREAM = "stream"


class ChatQueryParams(BaseModel):
    """请求参数模型"""

    collections: Optional[str] = Field(
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
        default=CONFIG.DEFAULT_INTENTION_MODEL,
        alias="intentionModel",
        description="意图模型",
    )
    generator_model: str = Field(
        default=CONFIG.DEFAULT_GENERATOR_MODEL,
        alias="generatorModel",
        description="生成模型",
    )
    generation_kwargs: str = Field(
        default="{}", alias="generationKwargs", description="生成参数"
    )
    tools: str = Field(
        None, alias="toolList", description="选用的工具，使用 , 分割，使用 all 为全部"
    )
    vin: str = Field(default="", alias="vin", description="设备的vin码")
    lat: float = Field(default=26.062731, alias="lat", description="纬度")
    lng: float = Field(default=119.235434, alias="lng", description="经度")
    city: str = Field(default="福州", alias="city", description="所在城市")

    class Config:
        populate_by_name = True

    @field_validator("tools", mode="after")
    def parse_tools(cls, v):
        return v.split(",") if v else []

    @field_validator("collections", mode="after")
    def parse_collections(cls, v):
        return v.split(",") if v else []


def get_prompt_template(prompt_name: str, db: Session) -> Optional[str]:
    """
    Obtain the prompt template from the database
    """

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
    """
    解析生成参数
    """
    if kwargs_str == "{}" or kwargs_str == "":
        return CONFIG.GENERATION_KWARGS
    try:
        return eval(kwargs_str)

    except Exception as e:
        logger.error("Failed to parse generation_kwargs: %s", str(e))
        return CONFIG.GENERATION_KWARGS


@router.get("/query")
@async_performance_logger
async def chat_rag(
    params: ChatQueryParams = Depends(),
    db: Session = Depends(get_db),
):
    logger.info("Processing query request, query: '%s'", params.query)

    # 获取提示词模板
    prefix_prompt = f"你的设备码是{params.vin}，当前时间{time.strftime('%Y-%m-%d %H:%M:%S')}，当前坐标({params.lat},{params.lng})，所在城市{params.city}"
    prompt_template = get_prompt_template(params.prompt_name, db)

    # 使用精准匹配模式，直接索引问题，然后匹配答案
    if params.precision_mode == 1:
        logger.info("Using precision mode for query: '%s'", params.query)
        answer = await QAQdrantDocumentStore(params.collections).query_exact(
            params.query
        )
        if answer:
            logger.info(
                "Found exact match for query: '%s'",
                params.query,
            )
            return Success(data=[{"content": answer, "role": "assistant"}])
        logger.info("No exact match found for query: '%s'", params.query)

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
    pipeline = RAGPipeline(
        qdrant_index=params.collections,
        intention_model=params.intention_model,
        generator_model=params.generator_model,
    )

    logger.debug("启动RAG管道查询: '%s'", params.query)
    response = await pipeline.run(
        query=params.query,
        tools=params.tools,
        top_k=params.top_k,
        prefix_prompt=prefix_prompt,
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

    # 初始化流处理器
    handler = StreamHandler()
    handler.start()

    # 获取参数
    is_batch = batch_or_stream == ProcessType.BATCH
    prefix_prompt = f"你的设备码是{params.vin}，当前时间{time.strftime('%Y-%m-%d %H:%M:%S')}，当前坐标({params.lat},{params.lng})，所在城市{params.city}\n"
    prompt_template = get_prompt_template(params.prompt_name, db)
    generation_kwargs = parse_generation_kwargs(params.generation_kwargs)

    # 获取历史消息
    history_messages = []
    if params.chat_id:
        history_messages = chat_cache.get_messages(params.chat_id, params.chat_rounds)
        logger.info(
            "处理查询: '%s'; 历史消息长度: %d; chat_id: %s",
            params.query,
            len(history_messages),
            params.chat_id,
        )

    # 处理精确模式查询的函数
    async def process_exact_query(answer):
        try:
            logger.debug("处理精确模式查询: %s", answer)
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
            logger.debug("启动RAG管道...")
            pipeline = RAGPipeline(
                qdrant_index=params.collections,
                intention_model=params.intention_model,
                generator_model=params.generator_model,
                stream_callback=handler.callback,
            )
            result = await pipeline.run(
                query=params.query,
                tools=params.tools,
                prefix_prompt=prefix_prompt,
                prompt_template=prompt_template,
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
        logger.info("使用精准模式进行流式查询")
        answer = await QAQdrantDocumentStore(params.collections[0]).query_exact(
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
