from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from chat2rag.core.logger import get_logger
from chat2rag.schemas.chat import ChatQueryParams
from chat2rag.services.chat_service import ChatProcessorV1

logger = get_logger(__name__)
router = APIRouter()


@router.get("/query-stream", summary="大模型交互V1", deprecated=True)
async def chat(params: ChatQueryParams = Depends()):
    """聊天V1接口"""
    processor = ChatProcessorV1(params.to_strategy_request())
    return StreamingResponse(processor.process(), media_type="text/event-stream")
