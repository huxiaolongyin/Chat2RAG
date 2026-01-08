from fastapi import APIRouter, Query
from tortoise.expressions import Q

from chat2rag.logger import get_logger
from chat2rag.schemas.base import BaseResponse, PaginatedResponse
from chat2rag.schemas.common import Current, Size
from chat2rag.schemas.expression import (
    RobotExpressionCreate,
    RobotExpressionData,
    RobotExpressionUpdate,
)
from chat2rag.services.expression_service import robot_expression_service

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=PaginatedResponse[RobotExpressionData], summary="获取机器人表情列表")
async def get_robot_expression_list(
    current: Current = 1,
    size: Size = 10,
    nameOrCode: str | None = Query(None, description="表情名称或代码", max_length=50),
    is_active: bool | None = Query(None, description="是否启用", alias="isActive"),
):

    q = Q()
    if nameOrCode:
        q &= Q(name__icontains=nameOrCode) | Q(code__icontains=nameOrCode)
    if is_active is not None:
        q &= Q(is_active=is_active)

    total, expressions = await robot_expression_service.get_list(current, size, q, order=["-id"])

    return PaginatedResponse.create(
        items=[RobotExpressionData.model_validate(expression) for expression in expressions],
        total=total,
        current=current,
        size=size,
    )


@router.get("/{expression_id}", response_model=BaseResponse[RobotExpressionData], summary="获取机器人表情详情")
async def get_robot_expression_detail(expression_id: int):
    expression = await robot_expression_service.get(expression_id)
    return BaseResponse.success(data=RobotExpressionData.model_validate(expression))


@router.post("", response_model=BaseResponse[RobotExpressionData], summary="创建机器人表情")
async def create_robot_expression(expression_in: RobotExpressionCreate):
    expression = await robot_expression_service.create(expression_in)
    return BaseResponse.success(data=RobotExpressionData.model_validate(expression))


@router.put("/{expression_id}", response_model=BaseResponse[RobotExpressionData], summary="更新机器人表情")
async def update_robot_expression(expression_id: int, expression_in: RobotExpressionUpdate):
    expression = await robot_expression_service.update(expression_id, expression_in)
    return BaseResponse.success(data=RobotExpressionData.model_validate(expression))


@router.delete("/{expression_id}", response_model=BaseResponse, summary="删除机器人表情")
async def delete_robot_expression(expression_id: int):
    await robot_expression_service.remove(expression_id)
    return BaseResponse.success(msg="删除成功")
