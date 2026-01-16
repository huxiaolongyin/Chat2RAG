from typing import Any, Dict

from fastapi import APIRouter
from tortoise.expressions import Q

from chat2rag.core.logger import get_logger
from chat2rag.schemas.base import BaseResponse, PaginatedResponse
from chat2rag.schemas.common import Current, Size
from chat2rag.schemas.flow_data import FlowCreate, FlowData, FlowUpdate
from chat2rag.services.flow_service import flow_service

logger = get_logger(__name__)
router = APIRouter()


@router.post("", response_model=BaseResponse[FlowData], summary="创建流程")
async def create_flow(flow_in: FlowCreate):
    flow = await flow_service.create(flow_in)
    return BaseResponse.success(msg="流程创建成功", data=FlowData.model_validate(flow))


@router.get("", response_model=PaginatedResponse[FlowData], summary="获取流程列表")
async def get_flow_list(current: Current = 1, size: Size = 10, name: str | None = None):

    q = Q()
    if name:
        q &= Q(name__icontains=name)

    total, flows = await flow_service.get_list(page=current, page_size=size, search=q)

    return PaginatedResponse.create(
        items=[FlowData.model_validate(flow) for flow in flows], total=total, current=current, size=size
    )


@router.get("/{id}", response_model=BaseResponse[FlowData], summary="获取流程明细")
async def get_flow_detail(id: int) -> Dict[str, Any]:
    flow = await flow_service.get(id)
    return BaseResponse.success(data=FlowData.model_validate(flow))


@router.put("/{id}", response_model=BaseResponse[FlowData], summary="更新流程")
async def update_flow(*, id: int, flow_in: FlowUpdate):

    flow = await flow_service.update(id, flow_in)
    return BaseResponse.success(data=FlowData.model_validate(flow))


@router.delete("/{id}", response_model=BaseResponse, summary="删除流程")
async def delete_flow(*, id: int):
    await flow_service.remove(id)
    return BaseResponse.success(msg="流程删除成功")
