from typing import Optional

from fastapi import APIRouter, Query
from tortoise.expressions import Q

from chat2rag.logger import auto_log, get_logger
from chat2rag.responses import Error, Success
from chat2rag.schemas.common import Current, Size
from chat2rag.schemas.expression import RobotExpressionCreate, RobotExpressionUpdate
from chat2rag.services.expression_service import RobotExpressionService

logger = get_logger(__name__)
router = APIRouter()
robot_expression_service = RobotExpressionService()


@router.get("/", summary="获取机器人表情列表")
@auto_log(level="info")
async def get_robot_expression_list(
    current: Current = 1,
    size: Size = 10,
    nameOrCode: Optional[str] = Query(
        None, description="表情名称或代码", max_length=50
    ),
    is_active: Optional[bool] = Query(None, description="是否启用", alias="isActive"),
):
    try:
        q = Q()
        if nameOrCode:
            q &= Q(name__icontains=nameOrCode) | Q(code__icontains=nameOrCode)
        if is_active is not None:
            q &= Q(is_active=is_active)

        total, expressions = await robot_expression_service.get_list(
            current,
            size,
            q,
            order=["-id"],
        )

        expression_list = [await exp.to_dict() for exp in expressions]

        return Success(
            data={
                "expressionList": expression_list,
                "total": total,
                "current": current,
                "size": size,
            }
        )
    except Exception as e:
        msg = f"获取机器人表情列表失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.get("/{expression_id}", summary="获取机器人表情详情")
@auto_log(level="info")
async def get_robot_expression_detail(expression_id: int):
    try:
        expression = await robot_expression_service.get(expression_id)
        if not expression:
            return Error(msg="表情不存在")

        return Success(data=await expression.to_dict())
    except Exception as e:
        msg = f"获取机器人表情详情失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.post("", summary="创建机器人表情")
@auto_log(level="info")
async def create_robot_expression(expression_in: RobotExpressionCreate):
    try:
        exist_name = await robot_expression_service.model.filter(
            name=expression_in.name
        ).first()
        if exist_name:
            return Error(msg="该表情名称已存在")

        exist_code = await robot_expression_service.model.filter(
            code=expression_in.code
        ).first()
        if exist_code:
            return Error(msg="该表情代码已存在")

        expression = await robot_expression_service.create(expression_in)
        return Success(data=await expression.to_dict())

    except Exception as e:
        msg = f"创建机器人表情失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.put("/{expression_id}", summary="更新机器人表情")
@auto_log(level="info")
async def update_robot_expression(
    expression_id: int, expression_in: RobotExpressionUpdate
):
    try:
        expression = await robot_expression_service.get(expression_id)
        if not expression:
            return Error(msg="表情不存在")

        if expression_in.name:
            exist_name = (
                await robot_expression_service.model.filter(name=expression_in.name)
                .exclude(id=expression_id)
                .first()
            )
            if exist_name:
                return Error(msg="该表情名称已存在")

        if expression_in.code:
            exist_code = (
                await robot_expression_service.model.filter(code=expression_in.code)
                .exclude(id=expression_id)
                .first()
            )
            if exist_code:
                return Error(msg="该表情代码已存在")

        expression = await robot_expression_service.update(expression_id, expression_in)
        return Success(data=await expression.to_dict())

    except Exception as e:
        msg = f"更新机器人表情失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.delete("/{expression_id}", summary="删除机器人表情")
@auto_log(level="info")
async def delete_robot_expression(expression_id: int):
    try:
        expression = await robot_expression_service.get(expression_id)
        if not expression:
            return Error(msg="表情不存在")

        await robot_expression_service.remove(expression_id)
        return Success(msg="删除成功")
    except Exception as e:
        msg = f"删除机器人表情失败: {str(e)}"
        logger.error(msg)
        return Error(msg)
