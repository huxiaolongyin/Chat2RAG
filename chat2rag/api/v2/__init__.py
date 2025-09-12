from fastapi import APIRouter

from .chat import router as chat_router

v2_router = APIRouter()


v2_router.include_router(router=chat_router, tags=["聊天"])
