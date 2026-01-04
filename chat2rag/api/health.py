from fastapi import APIRouter

from chat2rag.schemas.base import BaseResponse

router = APIRouter()

# fmt:off
@router.get("/health", response_model=BaseResponse[dict], summary="获取服务的健康状态", tags=["健康检查"])
async def get_service_health():
    # TODO: 数据库状态等等
    return BaseResponse.success(data={"API": "healthy"})
