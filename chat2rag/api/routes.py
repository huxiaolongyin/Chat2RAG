from datetime import datetime

from fastapi import APIRouter

from chat2rag.api.v1 import v1_router

router = APIRouter()


@router.get("/health", tags=["健康检查"])
async def _():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


router.include_router(router=v1_router, prefix="/v1")
# router.include_router(router=ws_router, tags=["流式"])
