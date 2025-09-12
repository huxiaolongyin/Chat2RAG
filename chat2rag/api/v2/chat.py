import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import lru_cache
from time import perf_counter
from typing import List, Tuple

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from haystack.dataclasses import ChatMessage, ChatRole, StreamingChunk
from sqlalchemy.orm import Session

from chat2rag.api.schema.chat import ChatRequest
from chat2rag.core.document.qdrant import QAQdrantDocumentStore
from chat2rag.core.process.process import handle_user_input
from chat2rag.database.connection import get_db
from chat2rag.enums import ProcessType
from chat2rag.logger import get_logger
from chat2rag.pipelines.agent import AgentPipeline
from chat2rag.utils.chat_history import ChatHistory
from chat2rag.utils.stream import StreamHandler

# from chat2rag.utils.monitoring import async_performance_logger
# from pyinstrument import Profiler
# profiler = Profiler()


logger = get_logger(__name__)
router = APIRouter()
chat_history = ChatHistory()

# To avoid creating a new executor for each request, which leads to resource waste, use a global executor
executor = ThreadPoolExecutor(max_workers=5)


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
    request: ChatRequest,
    handler: StreamHandler,
    start_time: float,
) -> StreamingResponse:
    """
    Handle precise queries
    """
    logger.info("Perform stream queries using the precise mode")

    try:
        query = request.content.get("text")
        answer = ""
        for collection in request.collections:
            res = await QAQdrantDocumentStore(collection).query_exact(query)
            if res:
                answer = res
                break

        if not answer:
            logger.info(
                "No exact match found for query: '%s', falling back to RAG",
                query,
            )
            return None

        logger.info("Found exact match for query: '%s'", query)
        asyncio.create_task(
            _stream_answer(
                answer,
                answer_source="Exact match answer",
                request=request,
                handler=handler,
                start_time=start_time,
            )
        )

        return StreamingResponse(
            handler.get_stream(True, input=request.content),
            media_type="text/event-stream",
            headers=_get_streaming_headers(),
        )
    except Exception as e:
        logger.error("Error in exact query: %s", str(e))
        return None


# async def _handle_process_answer(
#     answer: str,
#     request: ChatRequest,
#     handler: StreamHandler,
#     start_time: float,
# ):
#     """
#     Handle process answer
#     """
#     # logger.info("Perform stream queries using the precise mode")


async def _stream_answer(
    answer: str,
    answer_source: str,
    request: ChatRequest,
    handler: StreamHandler,
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
        if request.chat_id:
            chat_history.add_message(
                request.chat_id, ChatRole.USER, request.content.get("text")
            )
            chat_history.add_message(request.chat_id, ChatRole.ASSISTANT, answer)

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
    request: ChatRequest,
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
            collections=request.collections,
            model=request.model,
            tools=request.tools,
        )
        result = pipeline.run(
            query=request.content.get("text"),
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            doc_type="qa_pair",
            messages=history_messages,
            extra_params=request.extra_params
            | {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            streaming_callback=handler.callback,
        )

        # Update chat history
        messages: list = result.get("agent").get("messages")
        if request.chat_id and messages:
            new_messages = _get_latest_user_round(messages)
            chat_history.add_message(request.chat_id, messages=new_messages)

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


def record_info(handler: StreamHandler, request: ChatRequest):
    """
    Record the interaction information of the LLM
    """
    handler.set_chat_info(chat_id=request.chat_id, chat_rounds=request.chat_rounds)
    handler.set_query_info(
        question=request.content.get("text"), prompt=request.prompt_name
    )
    handler.set_collection_info(collections=request.collections)


async def _handle_process(
    request: ChatRequest,
    handler: StreamHandler,
    start_time: float,
) -> StreamingResponse:
    """
    Process procedural responses using state machines
    """
    answer = []
    query = request.content.get("text")
    for ans in handle_user_input(request.chat_id, query=query):
        answer.append(ans)
    if not answer:
        return

    try:
        # logger.info("Found exact match for query: '%s'", request.content.get("text"))
        asyncio.create_task(
            _stream_answer(
                "".join(answer),
                answer_source="Process answer",
                request=request,
                handler=handler,
                start_time=start_time,
            )
        )

        return StreamingResponse(
            handler.get_stream(True, input=request.content),
            media_type="text/event-stream",
            headers=_get_streaming_headers(),
        )
    except Exception as e:
        logger.error("Error in exact query: %s", str(e))
        return None


@router.post("/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    start_time = perf_counter()

    # Initialize the stream processor
    handler = StreamHandler()
    handler.start()
    record_info(handler=handler, request=request)

    # process & state
    if request.processes:
        process_answer = await _handle_process(request, handler, start_time)
        if process_answer:
            return process_answer

    # Exact mode query
    if request.precision_mode == 1:
        exact_answer = await _handle_exact_query(request, handler, start_time)
        if exact_answer:
            return exact_answer

    # Obtain parameters
    is_batch = request.batch_or_stream == ProcessType.BATCH
    history_messages = chat_history.get_history_messages(
        request.prompt_name, request.chat_id, db, request.chat_rounds
    )

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
        _process_agent_pipeline(request, handler, history_messages, start_time),
    )

    # Return flow response
    return StreamingResponse(
        handler.get_stream(is_batch, input=request.content),
        media_type="text/event-stream",
        headers=_get_streaming_headers(),
    )
