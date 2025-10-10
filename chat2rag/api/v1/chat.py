import ast
import asyncio
from enum import Enum
from time import perf_counter
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from haystack.dataclasses import ChatRole, StreamingChunk
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from chat2rag.api.schema import Error, Success
from chat2rag.config import CONFIG
from chat2rag.core.document.qdrant import QAQdrantDocumentStore
from chat2rag.core.executor import executor, run_async_in_thread
from chat2rag.database.connection import get_db
from chat2rag.database.models import Prompt
from chat2rag.logger import logger
from chat2rag.pipelines.rag_pipeline import RAGPipeline
from chat2rag.utils.chat_history import ChatHistory
from chat2rag.utils.pipeline_cache import create_pipeline
from chat2rag.utils.stream_v1 import StreamHandlerV1

router = APIRouter()
chat_history = ChatHistory()


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
        default=0.65,
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
    prompt_name: str = Field("默认", alias="promptName", description="提示词名称选择")
    intention_model: str = Field(
        default=CONFIG.DEFAULT_MODELS["intention"],
        alias="intentionModel",
        description="意图模型",
    )
    generator_model: str = Field(
        default=CONFIG.DEFAULT_MODELS["generator"],
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

    @field_validator("generator_model", mode="after")
    def parse_generator_model(cls, model):
        if model in CONFIG.MODEL_MAP:
            return CONFIG.MODEL_MAP[model]
        elif model in CONFIG.VALID_MODEL_VALUES:
            return model
        else:
            logger.warning(
                f"Invalid generator_model: {model!r}. Must be one of {sorted(CONFIG.VALID_MODEL_VALUES)}"
            )
            return CONFIG.DEFAULT_MODEL

    @field_validator("intention_model", mode="after")
    def parse_intention_model(cls, model):
        if model in CONFIG.MODEL_MAP:
            return CONFIG.MODEL_MAP[model]
        elif model in CONFIG.VALID_MODEL_VALUES:
            return model
        else:
            logger.warning(
                f"Invalid intention_model: {model!r}. Must be one of {sorted(CONFIG.VALID_MODEL_VALUES)}"
            )
            return CONFIG.DEFAULT_MODEL

    @field_validator("generation_kwargs", mode="after")
    def parse_generation_kwargs(cls, generation_kwargs):
        # Start with the default config
        merged_kwargs = dict(CONFIG.GENERATION_KWARGS)

        # If user provided non-empty and non-"{}" string, parse and update
        if generation_kwargs and generation_kwargs != "{}":
            try:
                user_kwargs = ast.literal_eval(generation_kwargs)
                if not isinstance(user_kwargs, dict):
                    raise ValueError("generation_kwargs must be a dictionary string.")
                merged_kwargs.update(user_kwargs)
            except (ValueError, SyntaxError) as e:
                raise ValueError(f"Invalid generation_kwargs format: {e}")

        return merged_kwargs


async def _stream_answer(
    answer: str,
    answer_source: str,
    params: ChatQueryParams,
    handler: StreamHandlerV1,
    start_time: float,
):
    """
    When there is a definite answer, The background sends the answer to the Stream handler
    """
    try:
        logger.debug(f"Processing {answer_source}: {answer}")

        chunk_size = 1
        for i in range(0, len(answer), chunk_size):
            chunk = answer[i : i + chunk_size]
            meta = {
                "model": "",
                "answer_source": answer_source,
                "finish_reason": "none",
            }
            handler.callback(StreamingChunk(content=chunk, meta=meta))
            await asyncio.sleep(0.001)

        # Send the end signal
        handler.callback(
            StreamingChunk(
                content="",
                meta={
                    "model": "",
                    "answer_source": answer_source,
                    "finish_reason": "stop",
                },
            )
        )

        # Update chat history
        if params.chat_id:
            chat_history.add_message(params.chat_id, ChatRole.USER, params.query)
            chat_history.add_message(params.chat_id, ChatRole.ASSISTANT, answer)

        logger.info(
            "Exact query processed successfully, took %.2fs",
            perf_counter() - start_time,
        )

    except Exception as e:
        logger.error("Error in exact query processing: %s", str(e))
        handler.callback(
            StreamingChunk(
                content=f"精确查询处理错误: {str(e)}",
                meta={"model": "error", "finish_reason": "error"},
            )
        )
    finally:
        handler.finish()


# 处理精确模式
async def _handle_exact_query(
    params: ChatQueryParams, handler: StreamHandlerV1, is_batch, start_time
):
    try:
        collection = params.collection_name
        query = params.query
        answer = await QAQdrantDocumentStore(collection).query_exact(query)

        if not answer:
            logger.info(
                "No relevant documents were found in the precise mode: '%s', falling back to RAG",
                query,
            )
            return None
        asyncio.create_task(
            _stream_answer(
                answer,
                answer_source="Exact match answer",
                params=params,
                handler=handler,
                start_time=start_time,
            )
        )
        return StreamingResponse(
            handler.get_stream(is_batch),
        )

    except Exception as e:
        logger.error("Error in exact query: %s", str(e))
        return None


async def _process_rag_pipeline(
    params: ChatQueryParams,
    history_messages: list,
    handler: StreamHandlerV1,
    start_time: float,
):
    """
    处理大模型、RAG的消息处理
    """
    try:
        pipeline = create_pipeline(
            RAGPipeline,
            qdrant_index=params.collection_name,
            intention_model=params.intention_model,
            generator_model=params.generator_model,
        )
        result = await pipeline.run(
            query=params.query,
            top_k=params.top_k,
            score_threshold=params.score_threshold,
            messages=history_messages,
            generation_kwargs=params.generation_kwargs,
            streaming_callback=handler.callback,
            start_time=start_time,
        )
        if params.chat_id:
            chat_history.add_message(
                params.chat_id,
                ChatRole.USER,
                params.query,
            )
            chat_history.add_message(
                params.chat_id,
                ChatRole.ASSISTANT,
                result["generator"]["replies"][0].text,
            )
    except Exception as e:
        logger.error("Error in pipeline: %s", str(e))
        # Send an error message to the stream
        handler.callback(
            StreamingChunk(
                content=f"处理请求时发生错误: {str(e)}",
                meta={"model": "error", "finish_reason": "error"},
            )
        )
    finally:
        # Make sure the stream is closed correctly
        handler.finish()


def record_info(handler: StreamHandlerV1, params: ChatQueryParams):
    """
    Record the interaction information of the LLM
    """
    handler.set_chat_info(chat_id=params.chat_id, chat_rounds=params.chat_rounds)
    handler.set_query_info(question=params.query, prompt=params.prompt_name)
    handler.set_collection_info(collections=params.collection_name)


@router.get("/query-stream")
async def _(
    params: ChatQueryParams = Depends(),
    batch_or_stream: ProcessType = Query(ProcessType.BATCH, alias="batchOrStream"),
    db: Session = Depends(get_db),
):
    logger.info(f"Chat Version: V1; Request params: {params}")
    start_time = perf_counter()
    handler = StreamHandlerV1()
    handler.start()
    record_info(handler=handler, params=params)
    is_batch = batch_or_stream == ProcessType.BATCH

    # 提示词
    prompt = (
        db.query(Prompt).filter(Prompt.prompt_name == params.prompt_name).first()
        if params.prompt_name
        else None
    )
    if not prompt:
        prompt = db.query(Prompt).filter(Prompt.prompt_name == "默认").first()

    # 使用精准匹配模式，直接索引问题，然后匹配答案
    if params.precision_mode == 1:
        exact_answer = await _handle_exact_query(params, handler, is_batch, start_time)
        if exact_answer:
            return exact_answer

    # 获取历史消息
    history_messages = []
    if params.chat_id:
        history_messages = chat_history.get_history_messages(
            params.prompt_name,
            params.chat_id,
            db,
            params.chat_rounds,
            tag_get=False,
        )

    # 启动后台任务
    executor.submit(
        run_async_in_thread,
        _process_rag_pipeline(params, history_messages, handler, start_time),
    )

    return StreamingResponse(
        handler.get_stream(is_batch),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Transfer-Encoding": "chunked",
        },
    )
