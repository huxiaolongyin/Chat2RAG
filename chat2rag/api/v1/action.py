from typing import Optional

from fastapi import APIRouter, Query
from tortoise.expressions import Q

from chat2rag.logger import auto_log, get_logger
from chat2rag.responses import Error, Success
from chat2rag.schemas.action import RobotActionCreate, RobotActionUpdate
from chat2rag.schemas.common import Current, Size
from chat2rag.services.action_service import RobotActionService

logger = get_logger(__name__)
robot_action_service = RobotActionService()
router = APIRouter()


@router.get("/", summary="获取机器人动作列表")
@auto_log(level="info")
async def get_robot_action_list(
    current: Current = 1,
    size: Size = 10,
    nameOrCode: Optional[str] = Query(
        None, description="动作名称或代码", max_length=50
    ),
    is_active: Optional[bool] = Query(None, description="是否启用", alias="isActive"),
):
    try:
        q = Q()
        if nameOrCode:
            q &= Q(name__icontains=nameOrCode) | Q(code__icontains=nameOrCode)
        if is_active is not None:
            q &= Q(is_active=is_active)

        total, actions = await robot_action_service.get_list(
            current,
            size,
            q,
            order=["-id"],
        )

        action_list = [await act.to_dict() for act in actions]

        return Success(
            data={
                "actionList": action_list,
                "total": total,
                "current": current,
                "size": size,
            }
        )
    except Exception as e:
        msg = f"获取机器人动作列表失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.get("/{action_id}", summary="获取机器人动作详情")
@auto_log(level="info")
async def get_robot_action_detail(action_id: int):
    try:
        action = await robot_action_service.get(action_id)
        if not action:
            return Error(msg="动作不存在")
        return Success(data=await action.to_dict())

    except Exception as e:
        msg = f"获取机器人动作详情失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.post("/", summary="创建机器人动作")
@auto_log(level="info")
async def create_robot_action(action_in: RobotActionCreate):
    try:
        exist_name = await robot_action_service.model.filter(
            name=action_in.name
        ).first()
        if exist_name:
            return Error(msg="该动作名称已存在")

        exist_code = await robot_action_service.model.filter(
            code=action_in.code
        ).first()
        if exist_code:
            return Error(msg="该动作代码已存在")

        action = await robot_action_service.create(action_in)
        return Success(data=await action.to_dict())

    except Exception as e:
        msg = f"创建机器人动作失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.put("/{action_id}", summary="更新机器人动作")
@auto_log(level="info")
async def update_robot_action(action_id: int, action_in: RobotActionUpdate):
    try:
        action = await robot_action_service.get(action_id)
        if not action:
            return Error(msg="动作不存在")

        if action_in.name:
            exist_name = (
                await robot_action_service.model.filter(name=action_in.name)
                .exclude(id=action_id)
                .first()
            )
            if exist_name:
                return Error(msg="该动作名称已存在")

        if action_in.code:
            exist_code = (
                await robot_action_service.model.filter(code=action_in.code)
                .exclude(id=action_id)
                .first()
            )
            if exist_code:
                return Error(msg="该动作代码已存在")

        action = await robot_action_service.update(action_id, action_in)
        return Success(data=await action.to_dict())

    except Exception as e:
        msg = f"更新机器人动作失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.delete("/{action_id}", summary="删除机器人动作")
@auto_log(level="info")
async def delete_robot_action(action_id: int):
    try:
        action = await robot_action_service.get(action_id)
        if not action:
            return Error(msg="动作不存在")

        await robot_action_service.remove(action_id)
        return Success(msg="删除成功")

    except Exception as e:
        msg = f"删除机器人动作失败: {str(e)}"
        logger.error(msg)
        return Error(msg)
