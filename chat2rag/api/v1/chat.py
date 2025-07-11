import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import lru_cache
from time import perf_counter
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from haystack.dataclasses import ChatMessage, StreamingChunk
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from chat2rag.api.schema import Success
from chat2rag.config import CONFIG
from chat2rag.core.database import get_db
from chat2rag.core.document.qdrant import QAQdrantDocumentStore
from chat2rag.enums import ProcessType
from chat2rag.logger import get_logger
from chat2rag.pipelines.agent import AgentPipeline
from chat2rag.utils.chat_history import ChatHistory
from chat2rag.utils.monitoring import async_performance_logger
from chat2rag.utils.stream import StreamHandler

# from pyinstrument import Profiler
# profiler = Profiler()

logger = get_logger(__name__)
router = APIRouter()
chat_history = ChatHistory()

# To avoid creating a new executor for each request, which leads to resource waste, use a global executor
executor = ThreadPoolExecutor(max_workers=5)


class ChatQueryParams(BaseModel):
    """
    Request parameter model for chat
    """

    collections: Optional[str] = Field(
        None,
        description="知识库名称，支持传入多个，用`,`划分",
    )
    query: str = Field(..., description="查询内容")
    top_k: int = Field(
        default=CONFIG.TOP_K,
        ge=0,
        le=30,
        alias="topK",
        description="文档检索的返回数量(0-30，默认5)",
    )
    score_threshold: float = Field(
        default=CONFIG.SCORE_THRESHOLD,
        ge=0.0,
        le=1.0,
        alias="scoreThreshold",
        description="文档匹配分数阈值(0-1.0，默认0.65)",
    )
    precision_mode: int = Field(
        default=0,
        alias="precisionMode",
        description="是否使用精确模式(0-不使用，1-使用，默认0)",
    )
    chat_id: Optional[str] = Field(
        None,
        alias="chatId",
        description="聊天会话的标识符，用于处理多轮聊天会话",
    )
    chat_rounds: int = Field(
        default=1,
        ge=0,
        le=30,
        alias="chatRounds",
        description="支持多轮对话的轮数(0-30，默认1)",
    )
    prompt_name: str = Field(
        "",
        alias="promptName",
        description="提示词名称选择(默认使用系统配置的提示词)",
    )

    model: str = Field(
        default=CONFIG.DEFAULT_MODEL,
        alias="model",
        description="生成模型(默认使用系统配置的模型)",
    )
    generation_kwargs: str | dict = Field(
        default=CONFIG.GENERATION_KWARGS,
        alias="generationKwargs",
        description="生成参数(默认使用系统配置的生成参数)",
    )
    tools: str = Field(
        None,
        description="选用的工具，使用 , 分割，使用 all 为全部",
    )
    extra_params: Optional[str] = Field(
        None,
        alias="extraParams",
        description="传入到 jinja 模板提示词中的额外参数",
    )

    class Config:
        populate_by_name = True

    @field_validator("tools", mode="after")
    def parse_tools(cls, v: str) -> List[str]:
        return v.split(",") if v else []

    @field_validator("collections", mode="after")
    def parse_collections(cls, v: str) -> List[str]:
        return v.split(",") if v else []

    @field_validator("model", mode="after")
    def parse_model(cls, v: str) -> str:
        for model in CONFIG.MODEL_LIST:
            if model["name"] == v:
                return model["id"]
        return v

    @field_validator("generation_kwargs", mode="after")
    def parse_generation_kwargs(cls, v: str):
        try:
            if isinstance(v, dict):
                return v
            return json.loads(v)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON string for generation_kwargs")

    @field_validator("extra_params", mode="after")
    def parse_extra_params(cls, v: str):
        try:
            if not v:
                return dict()
            return json.loads(v)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON string for extra_params")


@lru_cache(maxsize=32)
def _create_agent_pipeline(
    collections: Tuple[str, ...], model: str, tools: Tuple[str, ...]
) -> AgentPipeline:
    return AgentPipeline(list(collections), model, list(tools))


def create_pipeline(
    collections: List[str], model: str, tools: List[str]
) -> AgentPipeline:
    """
    lru_cache cant cache list, so we use this function to create a pipeline
    """
    return _create_agent_pipeline(tuple(collections), model, tuple(tools))


def _get_streaming_headers() -> dict:
    """
    Obtain the streaming response header
    """
    return {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Transfer-Encoding": "chunked",
    }


async def _handle_exact_query(
    params: ChatQueryParams, handler: StreamHandler, start_time: float
):
    """
    Handle precise queries
    """
    logger.info("Perform stream queries using the precise mode")

    try:
        answer = ""
        for collection in params.collections:
            res = await QAQdrantDocumentStore(collection).query_exact(params.query)
            if res:
                answer = res
                break

        if not answer:
            logger.info(
                "No exact match found for query: '%s', falling back to RAG",
                params.query,
            )
            return None

        logger.info("Found exact match for query: '%s'", params.query)
        asyncio.create_task(_stream_exact_answer(answer, params, handler, start_time))

        return StreamingResponse(
            handler.get_stream(True),
            media_type="text/event-stream",
            headers=_get_streaming_headers(),
        )
    except Exception as e:
        logger.error("Error in exact query: %s", str(e))
        return None


async def _stream_exact_answer(
    answer: str, params: ChatQueryParams, handler: StreamHandler, start_time: float
):
    """
    Stream the exact answer
    """
    try:
        logger.debug("Processing exact query: %s", answer)

        chunk_size = 50
        for i in range(0, len(answer), chunk_size):
            chunk = answer[i : i + chunk_size]
            meta = {"model": "exact_match", "finish_reason": "none"}
            handler.callback(StreamingChunk(content=chunk, meta=meta))
            await asyncio.sleep(0.001)

        # Send the end signal
        handler.callback(
            StreamingChunk(
                content="", meta={"model": "exact_match", "finish_reason": "stop"}
            )
        )

        # Update chat history
        if params.chat_id:
            chat_history.add_message(params.chat_id, params.query, "user")
            chat_history.add_message(params.chat_id, answer, "assistant")

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


def _get_latest_user_round(messages: List[ChatMessage]) -> List[ChatMessage]:
    """
    Get the latest round of conversations starting from the last role of user
    """
    if not messages:
        return []

    # Search for the position of the last user message from back to front
    last_user_index = -1
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].role == "user":
            last_user_index = i
            break

    # If a role of user message is found, return all messages from that position onwards
    if last_user_index != -1:
        return messages[last_user_index:]

    return []


async def _process_agent_pipeline(
    params: ChatQueryParams,
    handler: StreamHandler,
    history_messages: list,
    start_time: float,
):
    """
    Handle the pipeline processing of the agent.
    """
    try:
        # Start the profiler
        # profiler.start()
        logger.debug("start Agent pipeline...")

        pipeline = create_pipeline(
            collections=params.collections,
            model=params.model,
            tools=params.tools,
        )
        result = pipeline.run(
            query=params.query,
            top_k=params.top_k,
            score_threshold=params.score_threshold,
            doc_type="qa_pair",
            messages=history_messages,
            extra_params=params.extra_params
            | {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            streaming_callback=handler.callback,
        )

        # Update chat history
        messages: list = result.get("agent").get("messages")
        if params.chat_id and messages:
            new_messages = _get_latest_user_round(messages)
            chat_history.add_message(params.chat_id, messages=new_messages)

        logger.info(
            "Agent pipeline processed successfully, took %.2fs",
            perf_counter() - start_time,
        )
        # profiler.stop()
        # print(profiler.output_text(unicode=True, color=True))

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


@router.get("/query")
@async_performance_logger
async def chat_rag(params: ChatQueryParams = Depends(), db: Session = Depends(get_db)):
    logger.info("Processing query request, query: '%s'", params.query)

    # Get the prompt word template
    history_messages = chat_history.get_history_messages(
        params.prompt_name, params.chat_id, db, params.chat_rounds
    )

    # Use the exact match mode to directly index the questions and then match the answers
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

    # Create and run the pipeline
    pipeline = create_pipeline(
        collections=params.collections, model=params.model, tools=params.tools
    )

    logger.debug("Start pipeline query: '%s'", params.query)
    response = pipeline.run(
        query=params.query,
        top_k=params.top_k,
        score_threshold=params.score_threshold,
        doc_type="qa_pair",
        messages=history_messages,
        extra_params=params.extra_params
        | {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
    )

    # Process the returned result
    messages = response.get("agent").get("messages")
    new_messages = _get_latest_user_round(messages)
    data = []
    for message in new_messages[1:]:
        data.append(
            {
                "content": message.text,
                "role": message.role,
                "name": message.name,
                "meta": message.meta,
            }
        )

    # Update chat history
    if params.chat_id and new_messages:
        chat_history.add_message(params.chat_id, messages=new_messages)

    logger.info("Query processed successfully")
    return Success(data=data)


@router.get("/query-stream")
async def chat_rag_stream(
    params: ChatQueryParams = Depends(),
    batch_or_stream: ProcessType = Query(ProcessType.BATCH, alias="batchOrStream"),
    db: Session = Depends(get_db),
):
    start_time = perf_counter()

    # Initialize the stream processor
    handler = StreamHandler()
    handler.start()

    # Obtain parameters
    is_batch = batch_or_stream == ProcessType.BATCH
    history_messages = chat_history.get_history_messages(
        params.prompt_name, params.chat_id, db, params.chat_rounds
    )

    # Exact mode query
    if params.precision_mode == 1:
        exact_answer = await _handle_exact_query(params, handler, start_time)
        if exact_answer:
            return exact_answer

    # TODO: Need to optimize the performance of the following code
    # Key modification: Run the event loop using an independent thread
    def run_async_in_thread(coro):
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    # Submit the task to the thread pool
    executor.submit(
        run_async_in_thread,
        _process_agent_pipeline(params, handler, history_messages, start_time),
    )

    # Return flow response
    return StreamingResponse(
        handler.get_stream(is_batch),
        media_type="text/event-stream",
        headers=_get_streaming_headers(),
    )
