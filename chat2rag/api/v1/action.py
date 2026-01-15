from fastapi import APIRouter, Query
from tortoise.expressions import Q

from chat2rag.core.logger import get_logger
from chat2rag.schemas.action import (
    RobotActionCreate,
    RobotActionData,
    RobotActionUpdate,
)
from chat2rag.schemas.base import BaseResponse, PaginatedResponse
from chat2rag.schemas.common import Current, Size
from chat2rag.services.action_service import robot_action_service

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=PaginatedResponse[RobotActionData], summary="获取机器人动作列表")
async def get_robot_action_list(
    current: Current = 1,
    size: Size = 10,
    nameOrCode: str | None = Query(None, description="动作名称或代码", max_length=50),
    is_active: bool | None = Query(None, description="是否启用", alias="isActive"),
):
    q = Q()
    if nameOrCode:
        q &= Q(name__icontains=nameOrCode) | Q(code__icontains=nameOrCode)
    if is_active is not None:
        q &= Q(is_active=is_active)

    total, actions = await robot_action_service.get_list(current, size, q, order=["-id"])

    return PaginatedResponse.create(
        items=[RobotActionData.model_validate(action) for action in actions],
        total=total,
        current=current,
        size=size,
    )


@router.get("/{action_id}", response_model=BaseResponse[RobotActionData], summary="获取机器人动作详情")
async def get_robot_action_detail(action_id: int):
    action = await robot_action_service.get(action_id)
    return BaseResponse.success(data=RobotActionData.model_validate(action))


@router.post("", response_model=BaseResponse[RobotActionData], summary="创建机器人动作")
async def create_robot_action(action_in: RobotActionCreate):
    action = await robot_action_service.create(action_in)
    return BaseResponse.success(data=RobotActionData.model_validate(action))


@router.put("/{action_id}", response_model=BaseResponse[RobotActionData], summary="更新机器人动作")
async def update_robot_action(action_id: int, action_in: RobotActionUpdate):
    action = await robot_action_service.update(action_id, action_in)
    return BaseResponse.success(data=RobotActionData.model_validate(action))


@router.delete("/{action_id}", response_model=BaseResponse, summary="删除机器人动作")
async def delete_robot_action(action_id: int):
    await robot_action_service.remove(action_id)
    return BaseResponse.success(msg="删除成功")
