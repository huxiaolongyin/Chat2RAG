import contextlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from enum import Enum
from functools import wraps
from time import perf_counter
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from haystack.dataclasses import StreamingChunk
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.schema import Error, Success
from rag_core.config import CONFIG
from rag_core.database.database import get_db
from rag_core.database.models import Prompt, RAGPipelineMetrics
from rag_core.database.timescale import TimescaleDB
from rag_core.document.qdrant import QAQdrantDocumentStore
from rag_core.logging import logger
from rag_core.pipelines.rag_pipeline import RAGPipeline
from rag_core.tools import ToolManager
from rag_core.utils.chat_cache import ChatCache
from rag_core.utils.metric import MetricsRecorder
from rag_core.utils.stream import StreamHandler


class ProcessType(str, Enum):
    """处理类型"""

    FULL = "full"
    BATCH = "batch"
    STREAM = "stream"


class Config:
    """配置常量集中管理"""

    DEFAULT_MODELS = {
        "intention": "Qwen/Qwen2.5-14B-Instruct",
        "generator": "Qwen/Qwen2.5-32B-Instruct",
    }

    GENERATION_KWARGS = {
        "temperature": 0.1,
        "presence_penalty": -0.2,
        "max_tokens": 150,
    }


class ChatQueryParams(BaseModel):
    """请求参数模型"""

    collection_name: Optional[str] = Field(
        None, alias="collectionName", description="知识库名称"
    )
    query: str = Field(..., description="查询内容")
    top_k: int = Field(default=5, ge=0, le=30, alias="topK", description="返回数量")
    score_threshold: float = Field(
        default=0.6,
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


class PipelineMetrics:
    """性能监控类"""

    def __init__(self):
        self.start_time = perf_counter()
        self.steps = {}

    def record_step(self, step_name: str):
        self.steps[step_name] = perf_counter() - self.start_time

    def get_total_time(self):
        return perf_counter() - self.start_time


@contextlib.asynccontextmanager
async def get_pipeline(
    collection_name: str, intention_model: str, generator_model: str
):
    """Pipeline上下文管理"""
    pipeline = RAGPipeline(
        qdrant_index=collection_name,
        intention_model=intention_model,
        generator_model=generator_model,
    )
    try:
        yield pipeline
    finally:
        pass


async def handle_precision_query(
    params: ChatQueryParams,
    process_type: ProcessType,
    metrics: PipelineMetrics,
    handler: Optional[StreamHandler] = None,
) -> Optional[Dict]:
    """精确查询处理"""
    answer = await QAQdrantDocumentStore(params.collection_name).query_exact(
        params.query
    )
    if not answer:
        return None

    metrics.record_step("exact_match")

    if process_type == ProcessType.FULL:
        return Success(data=[{"content": answer, "role": "assistant"}])

    return await stream_exact_response(params, answer, handler)


async def stream_exact_response(
    params: ChatQueryParams, answer: str, handler: StreamHandler
) -> bool:
    """处理精确匹配的流式响应"""

    def process_stream():
        handler.start()
        for chunk in answer:
            handler.callback(
                StreamingChunk(
                    content=chunk, meta={"model": "None", "finish_reason": "none"}
                )
            )

        handler.callback(
            StreamingChunk(content="", meta={"model": "None", "finish_reason": "stop"})
        )
        handler.finish()

        # 更新聊天历史
        if params.chat_id:
            chat_cache.add_message(params.chat_id, params.query, "user")
            chat_cache.add_message(params.chat_id, answer, "assistant")

    with ThreadPoolExecutor(max_workers=1) as executor:
        executor.submit(process_stream)

    return True


def log_pipeline_metrics(
    recorder: MetricsRecorder,
    chat_id: str,
    query: str,
    answer: str,
):
    """
    记录pipeline的指标到数据库
    """
    timeimescale_db.insert_metric(
        RAGPipelineMetrics(
            time=datetime.now(),
            chat_id=chat_id,
            type="stream",
            question=query,
            answer=answer,
            document_ms=recorder.metrics.get("document_retrieval"),
            function_ms=recorder.metrics.get("function_call"),
            rag_response_ms=recorder.metrics.get("rag_generation"),
            total_ms=recorder.get_total_time() * 1000,
            status="success",
        )
    )


def handle_chat_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Chat error: {str(e)}")
            return Error(msg="Chat error", data=str(e))

    return wrapper


def get_prompt_template(db: Session, prompt_name: str = None) -> Optional[Prompt]:
    """获取prompt模板"""
    result = CONFIG.RAG_PROMPT_TEMPLATE
    prompt = db.query(Prompt).filter(Prompt.prompt_name == prompt_name).first()
    if prompt:
        result = prompt.prompt_text
    return result


router = APIRouter()
chat_cache = ChatCache()
tool_manager = ToolManager()
timeimescale_db = TimescaleDB()


async def handle_precision_query(
    collection_name: str,
    query: str,
    chat_id: Optional[str],
    process_type: ProcessType,
    recorder: MetricsRecorder,
    handler: StreamHandler = None,
) -> Optional[Dict]:
    """精确查询处理"""
    answer = await QAQdrantDocumentStore(collection_name).query_exact(query)
    if not answer:
        return None

    if process_type == ProcessType.FULL:
        recorder.record_step("total")
        return Success(data=[{"content": answer, "role": "assistant"}])

    def stream_response():
        handler.start()
        for chunk in answer:
            handler.callback(
                StreamingChunk(
                    content=chunk, meta={"model": "None", "finish_reason": "none"}
                )
            )
        handler.callback(
            StreamingChunk(content="", meta={"model": "None", "finish_reason": "stop"})
        )
        handler.finish()

        if chat_id:
            chat_cache.add_message(chat_id, query, "user")
            chat_cache.add_message(chat_id, answer, "assistant")

    with ThreadPoolExecutor(max_workers=1) as executor:
        executor.submit(stream_response)
    return True


def create_streaming_response(handler, is_batch):
    """创建流式响应"""
    return StreamingResponse(
        handler.get_stream(is_batch),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Transfer-Encoding": "chunked",
        },
    )


@router.get("/query")
@handle_chat_errors
async def chat_query(
    params: ChatQueryParams = Depends(), db: Session = Depends(get_db)
):
    recorder = MetricsRecorder()

    if params.precision_mode:
        result = await handle_precision_query(
            params.collection_name,
            params.query,
            params.chat_id,
            ProcessType.FULL,
            recorder,
        )
        if result:
            return result

    async with get_pipeline(
        params.collection_name, params.intention_model, params.generator_model
    ) as pipeline:
        response = await pipeline.arun(
            query=params.query,
            tools=tool_manager.get_tool_info(params.tool_list),
            messages=chat_cache.get_messages(params.chat_id, params.chat_rounds),
            generation_kwargs=Config.GENERATION_KWARGS,
        )

    return Success(data=[chat.to_dict() for chat in response["generator"]["replies"]])


@router.get("/query-stream")
async def stream_chat_query(
    params: ChatQueryParams = Depends(),
    batch_or_stream: ProcessType = Query(ProcessType.BATCH),
):
    """流式查询接口"""
    recorder = MetricsRecorder()
    handler = StreamHandler()

    if params.precision_mode:
        result = await handle_precision_query(
            params.collection_name,
            params.query,
            params.chat_id,
            batch_or_stream,
            recorder,
            handler,
        )

        if result:
            return create_streaming_response(
                handler, batch_or_stream == ProcessType.BATCH
            )

    async with get_pipeline(
        params.collection_name, params.intention_model, params.generator_model
    ) as pipeline:
        pipeline.stream_callback = handler.callback

        def process_response():
            pipeline.run(
                query=params.query,
                tools=tool_manager.get_tool_info(params.tool_list),
                messages=chat_cache.get_messages(params.chat_id, params.chat_rounds),
                generation_kwargs=Config.GENERATION_KWARGS,
                metrics=recorder,
            )
            handler.finish()

        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(process_response)

    return create_streaming_response(handler, batch_or_stream == ProcessType.BATCH)
