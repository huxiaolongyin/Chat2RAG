from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from time import perf_counter
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from haystack.dataclasses import StreamingChunk
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.schema import Error, Success
from rag_core.config import CONFIG
from rag_core.database.database import get_db
from rag_core.database.models import Prompt
from rag_core.document.qdrant import QAQdrantDocumentStore
from rag_core.logging import logger
from rag_core.pipelines.rag_pipeline import RAGPipeline
from rag_core.tools import ToolManager
from rag_core.utils.chat_cache import ChatCache
from rag_core.utils.stream import StreamHandler

router = APIRouter()
chat_cache = ChatCache()
tool_manager = ToolManager()


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


@router.get("/query")
async def _(
    params: ChatQueryParams = Depends(),
    db: Session = Depends(get_db),
):
    start = perf_counter()

    # 提示词
    if params.prompt_name:
        prompt = (
            db.query(Prompt).filter(Prompt.prompt_name == params.prompt_name).first()
        )
        if prompt:
            rag_prompt_template = prompt.prompt_text

    # 使用精准匹配模式，直接索引问题，然后匹配答案
    if params.precision_mode == 1:
        answer = await QAQdrantDocumentStore(params.collection_name).query_exact(
            params.query
        )
        if answer:
            return Success(data=[{"content": answer, "role": "assistant"}])

    # 获取使用的工具信息
    tools = tool_manager.get_tool_info(params.tool_list)

    # 获取历史消息
    history_messages = []
    if params.chat_id:
        history_messages = chat_cache.get_messages(params.chat_id, params.chat_rounds)

    if params.generation_kwargs == "{}" or params.generation_kwargs == "":
        generation_kwargs = {
            "temperature": 0.1,
            "presence_penalty": -0.2,
            "max_tokens": 150,
        }
    else:
        generation_kwargs = eval(params.generation_kwargs)

    pipeline = RAGPipeline(
        qdrant_index=params.collection_name,
        intention_model=params.intention_model,
        generator_model=params.generator_model,
    )
    response = await pipeline.arun(
        query=params.query,
        tools=tools,
        top_k=params.top_k,
        rag_prompt_template=rag_prompt_template,
        score_threshold=params.score_threshold,
        messages=history_messages,
        generation_kwargs=generation_kwargs,
        start=start,
    )
    chat_list = response.get("generator").get("replies")
    data = [chat.to_dict() for chat in chat_list]
    return Success(data=data)


@router.get("/query-stream")
async def _(
    params: ChatQueryParams = Depends(),
    batch_or_stream: ProcessType = Query(ProcessType.BATCH, alias="batchOrStream"),
    db: Session = Depends(get_db),
):
    start = perf_counter()
    handler = StreamHandler()
    tools = tool_manager.get_tool_info(params.tool_list)
    is_batch = batch_or_stream == ProcessType.BATCH

    # 提示词
    rag_prompt_template = CONFIG.RAG_PROMPT_TEMPLATE
    if params.prompt_name:
        prompt = (
            db.query(Prompt).filter(Prompt.prompt_name == params.prompt_name).first()
        )
        if prompt:
            rag_prompt_template = prompt.prompt_text

    executor = ThreadPoolExecutor(max_workers=1)  # 创建全局executor避免提前关闭

    # 处理精确模式
    def run_exact_query():
        handler.start()
        for i in answer:
            meta = {"model": "None", "finish_reason": "none"}
            handler.callback(StreamingChunk(content=i, meta=meta))

        handler.callback(
            StreamingChunk(content="", meta={"model": "None", "finish_reason": "stop"})
        )
        handler.finish()
        if params.chat_id:
            chat_cache.add_message(params.chat_id, params.query, "user")
            chat_cache.add_message(params.chat_id, answer, "assistant")

    # 处理大模型、RAG的消息处理
    def run_rag_pipeline():
        result = pipeline.run(
            query=params.query,
            rag_prompt_template=rag_prompt_template,
            tools=tools,
            top_k=params.top_k,
            score_threshold=params.score_threshold,
            messages=history_messages,
            generation_kwargs=generation_kwargs,
            start=start,
        )
        handler.finish()
        if params.chat_id:
            chat_cache.add_message(params.chat_id, params.query, "user")
            chat_cache.add_message(
                params.chat_id, result["generator"]["replies"][0].content, "assistant"
            )

    # 使用精准匹配模式，直接索引问题，然后匹配答案
    if params.precision_mode == 1:
        answer = await QAQdrantDocumentStore(params.collection_name).query_exact(
            params.query
        )
        logger.info(
            f"RAG pipeline ran successfully. Query: <{params.query}>; Answer: <{answer}>"
        )
        logger.info(f"RAG pipeline query finished, cost {perf_counter() - start:.2f}s")
        if answer:
            # 启动后台任务
            executor.submit(run_exact_query)

            return StreamingResponse(
                handler.get_stream(is_batch),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Transfer-Encoding": "chunked",
                },
            )

    if params.generation_kwargs == "{}":
        generation_kwargs = {
            "temperature": 0.1,
            "presence_penalty": -0.2,
            "max_tokens": 150,
        }
    else:
        generation_kwargs = eval(params.generation_kwargs)

    # 获取历史消息
    history_messages = []
    if params.chat_id:
        history_messages = chat_cache.get_messages(params.chat_id, params.chat_rounds)

    pipeline = RAGPipeline(
        qdrant_index=params.collection_name,
        stream_callback=handler.callback,
        intention_model=params.intention_model,
        generator_model=params.generator_model,
    )

    # 启动后台任务
    executor.submit(run_rag_pipeline)

    return StreamingResponse(
        handler.get_stream(is_batch),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Transfer-Encoding": "chunked",
        },
    )
