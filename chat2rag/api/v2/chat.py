from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from chat2rag.core.logger import get_logger
from chat2rag.schemas.chat import ChatRequest
from chat2rag.services.chat_service import ChatProcessor

logger = get_logger(__name__)
router = APIRouter()


@router.post("/chat")
async def chat(chat_request: ChatRequest):
    """聊天接口"""
    chat_request.tools = [
        "maps_weather",
        "maps_geo",
        "maps_direction_transit_integrated",
        "web_search",
        "cart_manage",
        "checkout",
        "get_train_info",
        "search_entities",
        "confirm_navigate",
    ]
    processor = ChatProcessor(chat_request)
    return StreamingResponse(processor.process(), media_type="text/event-stream")
