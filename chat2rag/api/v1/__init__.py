from fastapi import APIRouter

from .auth import router as auth_router
from .chat import router as chat_router
from .document import router as knowledge_router
from .flow import router as flow_router
from .metrics import router as metrics_router
from .model import router as model_router
from .prompt import router as prompt_router
from .tools import router as tools_router
from .version import router as version_router

v1_router = APIRouter()

v1_router.include_router(router=knowledge_router, prefix="/knowledge", tags=["知识库"])
v1_router.include_router(router=tools_router, prefix="/tools", tags=["工具"])
v1_router.include_router(router=prompt_router, prefix="/prompt", tags=["提示词"])
v1_router.include_router(router=model_router, prefix="/model", tags=["模型"])
v1_router.include_router(router=chat_router, prefix="/chat", tags=["聊天"])
v1_router.include_router(router=auth_router, prefix="/auth", tags=["认证"])
v1_router.include_router(router=metrics_router, prefix="/metrics", tags=["指标"])
v1_router.include_router(router=flow_router, prefix="/flow", tags=["流程"])
v1_router.include_router(router=version_router, prefix="/version", tags=["版本"])
