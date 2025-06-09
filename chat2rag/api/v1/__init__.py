from fastapi import APIRouter

from .chat import router as chat_router
from .document import router as knowledge_router
from .model import router as model_router
from .prompt import router as prompt_router
from .tools import router as tools_router

v1_router = APIRouter()

v1_router.include_router(router=knowledge_router, prefix="/knowledge", tags=["知识库"])
v1_router.include_router(router=tools_router, prefix="/tools", tags=["工具"])
v1_router.include_router(router=prompt_router, prefix="/prompt", tags=["提示词"])
v1_router.include_router(router=model_router, prefix="/model", tags=["模型"])
v1_router.include_router(router=chat_router, prefix="/chat", tags=["聊天"])
