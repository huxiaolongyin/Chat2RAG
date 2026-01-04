from fastapi import APIRouter

from chat2rag.api.health import router as health_router
from chat2rag.api.v1 import v1_router
from chat2rag.api.v2 import v2_router

router = APIRouter()

router.include_router(router=health_router)
router.include_router(router=v1_router, prefix="/v1")
router.include_router(router=v2_router, prefix="/v2")
