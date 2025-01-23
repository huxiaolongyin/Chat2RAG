from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from time import perf_counter

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from haystack.dataclasses import StreamingChunk
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


# 使用枚举
class ProcessType(str, Enum):
    BATCH = "batch"
    STREAM = "stream"


@router.get("/query")
async def _(
    collection_name: str = Query(
        None,
        description="知识库名称",
        alias="collectionName",
    ),
    query: str = Query(
        description="查询内容",
        alias="query",
    ),
    top_k: int = Query(
        default=5,
        ge=0,
        le=30,
        description="返回数量",
        alias="topK",
    ),
    score_threshold: float = Query(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="文档匹配分数阈值",
        alias="scoreThreshold",
    ),
    precision_mode: int = Query(
        default=0,
        description="是否使用精确模式",
        alias="precisionMode",
    ),
    chat_id: str = Query(
        None,
        description="聊天的标识",
        alias="chatId",
    ),
    chat_rounds: int = Query(
        default=1,
        ge=0,
        le=30,
        description="聊天轮数",
        alias="chatRounds",
    ),
    prompt_name: str = Query(
        default="",
        description="提示词名称选择",
        alias="promptName",
    ),
    intention_model: str = Query(
        default="Qwen/Qwen2.5-14B-Instruct",
        description="意图模型",
        alias="intentionModel",
    ),
    generator_model: str = Query(
        default="Qwen/Qwen2.5-32B-Instruct",
        description="生成模型",
        alias="generatorModel",
    ),
    tool_list: list = Query(
        default=[],
        description="工具列表",
        alias="toolList",
    ),
    generation_kwargs: str = Query(
        default="{}",
        description="生成参数",
        alias="generationKwargs",
    ),
    db: Session = Depends(get_db),
):
    start = perf_counter()

    # 提示词
    rag_prompt_template = CONFIG.RAG_PROMPT_TEMPLATE
    if prompt_name:
        prompt = db.query(Prompt).filter(Prompt.prompt_name == prompt_name).first()
        if prompt:
            rag_prompt_template = prompt.prompt_text

    # 使用精准匹配模式，直接索引问题，然后匹配答案
    if precision_mode == 1:
        answer = await QAQdrantDocumentStore(collection_name).query_exact(query)
        if answer:
            return Success(data=[{"content": answer, "role": "assistant"}])

    # 获取使用的工具信息
    tools = tool_manager.get_tool_info(tool_list)

    # 获取历史消息
    history_messages = []
    if chat_id:
        history_messages = chat_cache.get_messages(chat_id, chat_rounds)

    if generation_kwargs == "{}" or generation_kwargs == "":
        generation_kwargs = {
            "temperature": 0.1,
            "presence_penalty": -0.2,
            "max_tokens": 150,
        }
    else:
        generation_kwargs = eval(generation_kwargs)

    pipeline = RAGPipeline(
        qdrant_index=collection_name,
        intention_model=intention_model,
        generator_model=generator_model,
    )
    response = await pipeline.arun(
        query=query,
        tools=tools,
        top_k=top_k,
        rag_prompt_template=rag_prompt_template,
        score_threshold=score_threshold,
        messages=history_messages,
        generation_kwargs=generation_kwargs,
        start=start,
    )
    chat_list = response.get("generator").get("replies")
    data = [chat.to_dict() for chat in chat_list]
    return Success(data=data)


@router.get("/query-stream")
async def _(
    collection_name: str = Query(
        None,
        description="   ",
        alias="collectionName",
    ),
    query: str = Query(
        description="查询内容",
        alias="query",
    ),
    top_k: int = Query(
        default=5,
        ge=0,
        le=30,
        description="返回数量",
        alias="topK",
    ),
    score_threshold: float = Query(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="文档匹配分数阈值",
        alias="scoreThreshold",
    ),
    batch_or_stream: ProcessType = Query(
        ProcessType.BATCH,
        description="批量或流式",
        alias="batchOrStream",
    ),
    precision_mode: int = Query(
        default=0,
        description="是否使用精确模式",
        alias="precisionMode",
    ),
    chat_id: str = Query(
        None,
        description="聊天的标识",
        alias="chatId",
    ),
    chat_rounds: int = Query(
        default=1,
        ge=0,
        le=30,
        description="聊天轮数",
        alias="chatRounds",
    ),
    prompt_name: str = Query(
        default="",
        description="提示词名称选择",
        alias="promptName",
    ),
    intention_model: str = Query(
        default="Qwen/Qwen2.5-14B-Instruct",
        description="意图模型",
        alias="intentionModel",
    ),
    generator_model: str = Query(
        default="Qwen/Qwen2.5-32B-Instruct",
        description="生成模型",
        alias="generatorModel",
    ),
    tool_list: str = Query(
        default="[]",
        description="工具列表",
        alias="toolList",
    ),
    generation_kwargs: str = Query(
        default="{}",
        description="生成参数",
        alias="generationKwargs",
    ),
    db: Session = Depends(get_db),
):
    start = perf_counter()
    handler = StreamHandler()
    tools = tool_manager.get_tool_info(eval(tool_list))
    is_batch = batch_or_stream == ProcessType.BATCH

    # 提示词
    rag_prompt_template = CONFIG.RAG_PROMPT_TEMPLATE
    if prompt_name:
        prompt = db.query(Prompt).filter(Prompt.prompt_name == prompt_name).first()
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
        if chat_id:
            chat_cache.add_message(chat_id, query, "user")
            chat_cache.add_message(chat_id, answer, "assistant")

    # 处理大模型、RAG的消息处理
    def run_rag_pipeline():
        result = pipeline.run(
            query=query,
            rag_prompt_template=rag_prompt_template,
            tools=tools,
            top_k=top_k,
            score_threshold=score_threshold,
            messages=history_messages,
            generation_kwargs=generation_kwargs,
            start=start,
        )
        handler.finish()
        if chat_id:
            chat_cache.add_message(chat_id, query, "user")
            chat_cache.add_message(
                chat_id, result["generator"]["replies"][0].content, "assistant"
            )

    # 使用精准匹配模式，直接索引问题，然后匹配答案
    if precision_mode == 1:
        answer = await QAQdrantDocumentStore(collection_name).query_exact(query)
        logger.info(
            f"RAG pipeline ran successfully. Query: <{query}>; Answer: <{answer}>"
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

    if generation_kwargs == "{}":
        generation_kwargs = {
            "temperature": 0.1,
            "presence_penalty": -0.2,
            "max_tokens": 150,
        }
    else:
        generation_kwargs = eval(generation_kwargs)

    # 获取历史消息
    history_messages = []
    if chat_id:
        history_messages = chat_cache.get_messages(chat_id, chat_rounds)

    pipeline = RAGPipeline(
        qdrant_index=collection_name,
        stream_callback=handler.callback,
        intention_model=intention_model,
        generator_model=generator_model,
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
