from datetime import datetime

from fastapi import APIRouter

from chat2rag.api.v1 import v1_router
from chat2rag.api.v2 import v2_router

router = APIRouter()


@router.get("/health", summary="健康检查", tags=["健康检查"])
async def _():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


router.include_router(router=v1_router, prefix="/v1")
router.include_router(router=v2_router, prefix="/v2")
# router.include_router(router=ws_router, tags=["流式"])
