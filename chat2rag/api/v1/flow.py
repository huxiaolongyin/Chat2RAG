from typing import Any, Dict, Optional

from fastapi import APIRouter
from tortoise.expressions import Q

from chat2rag.logger import get_logger
from chat2rag.responses import Error, Success
from chat2rag.schemas.common import Current, Size
from chat2rag.schemas.flow_data import FlowDataCreate, FlowDataUpdate
from chat2rag.services.flow_service import FlowDataService

logger = get_logger(__name__)
router = APIRouter()
flow_service = FlowDataService()


@router.post("", summary="创建流程")
async def create_flow(*, flow_in: FlowDataCreate) -> Dict[str, Any]:
    try:
        exist_flow = await flow_service.model.filter(name=flow_in.name).first()
        if exist_flow:
            return Error(msg="该流程已存在")
        flow = await flow_service.create(flow_in)
        return Success(msg="流程创建成功", data=await flow.to_dict())
    except Exception as e:
        msg = f"创建流程失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.get("", response_model=Dict[str, Any], summary="获取流程列表")
async def get_flow_list(
    *,
    current: Current = 1,
    size: Size = 10,
    name: Optional[str] = None,
) -> Dict[str, Any]:

    try:
        q = Q()
        if name:
            q &= Q(name__icontains=name)
        total, flows = await flow_service.get_list(page=current, page_size=size, search=q)

        return Success(
            data={
                "flowList": [await flow.to_dict() for flow in flows],
                "total": total,
                "current": current,
                "size": size,
            },
        )
    except Exception as e:
        msg = f"获取流程列表失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.get("/{id}", summary="获取流程明细")
async def get_flow_detail(*, id: int) -> Dict[str, Any]:
    try:
        flow = await flow_service.get(id)
        if not flow:
            return Error(msg="流程数据不存在")
        return Success(data=await flow.to_dict())
    except Exception as e:
        msg = f"获取流程失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.put("/{id}", response_model=Dict[str, Any], summary="更新流程")
async def update_flow(*, id: int, flow_in: FlowDataUpdate) -> Dict[str, Any]:
    try:
        flow = await flow_service.get(id)
        if not flow:
            return Error(msg="流程数据不存在")
        exist_flow = await flow_service.model.filter(name=flow_in.name).first()
        if exist_flow:
            return Error(msg="该分类已存在")
        flow = await flow_service.update(id, flow_in)
        return Success(data=await flow.to_dict())
    except Exception as e:
        msg = f"更新流程失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.delete("/{id}", response_model=Dict[str, Any], summary="删除流程")
async def delete_flow(*, id: int) -> Dict[str, Any]:
    try:
        flow = await flow_service.get(id)
        if not flow:
            return Error(msg="流程数据不存在")
        await flow_service.remove(id)
        return Success(msg="删除成功")
    except Exception as e:
        msg = f"流程数据不存在:{str(e)}"
        logger.error(msg)
        return Error(msg)
