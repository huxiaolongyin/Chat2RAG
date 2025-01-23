from datetime import datetime

from fastapi import APIRouter

from backend.api.v1 import chat_router, knowledge_router, prompt_router, tools_router

router = APIRouter()


@router.get("/health", tags=["健康检查"])
async def _():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


router.include_router(router=knowledge_router, prefix="/knowledge", tags=["知识库"])
router.include_router(router=tools_router, prefix="/tools", tags=["工具"])
router.include_router(router=chat_router, prefix="/chat", tags=["聊天"])
router.include_router(router=prompt_router, prefix="/prompt", tags=["提示词"])
