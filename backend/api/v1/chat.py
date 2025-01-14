from concurrent.futures import ThreadPoolExecutor
from enum import Enum

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from backend.schema import Error, Success
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
):
    # 获取使用的工具信息
    tools = tool_manager.get_tool_info(tool_list)

    # 获取历史消息
    history_messages = []
    if chat_id:
        history_messages = chat_cache.get_messages(chat_id, chat_rounds)

    if generation_kwargs == "{}":
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
        score_threshold=score_threshold,
        messages=history_messages,
        generation_kwargs=generation_kwargs,
    )
    chat_list = response.get("generator").get("replies")
    data = [chat.to_dict() for chat in chat_list]
    return Success(data=data)


@router.get("/query-stream")
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
    batch_or_stream: ProcessType = Query(
        ProcessType.BATCH,
        description="批量或流式",
        alias="batchOrStream",
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
):
    # print(eval(tool_list))
    handler = StreamHandler()
    # handler.start()
    tools = tool_manager.get_tool_info(eval(tool_list))

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

    # 创建全局executor避免提前关闭
    executor = ThreadPoolExecutor(max_workers=1)

    def run_rag_pipeline():
        result = pipeline.run(
            query=query,
            tools=tools,
            top_k=top_k,
            score_threshold=score_threshold,
            messages=history_messages,
            generation_kwargs=generation_kwargs,
        )
        handler.finish()
        if chat_id:
            chat_cache.add_message(chat_id, query, "user")
            chat_cache.add_message(
                chat_id, result["generator"]["replies"][0].content, "assistant"
            )

    # 启动后台任务
    executor.submit(run_rag_pipeline)
    is_batch = batch_or_stream == ProcessType.BATCH

    return StreamingResponse(
        handler.get_stream(is_batch),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Transfer-Encoding": "chunked",
        },
    )
