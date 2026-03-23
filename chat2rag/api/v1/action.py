import io

import pandas as pd
from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import StreamingResponse
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


@router.get("/template", summary="下载动作导入模板")
async def download_template():
    data = [
        {
            "名称": "挥手",
            "代码": "WaveHands",
            "是否启用": "是",
            "描述": "用于机器人上下摆动右手",
        },
        {
            "名称": "点头",
            "代码": "NodHead",
            "是否启用": "是",
            "描述": "用于机器人点头表示同意",
        },
    ]

    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="动作模板")
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=action_template.xlsx"},
    )


@router.get("/export", summary="导出动作")
async def export_actions(
    format: str = Query("xlsx", description="导出格式: xlsx 或 csv"),
    is_active: bool = Query(None, description="是否启用", alias="isActive"),
    action_ids: str = Query(
        None, description="选中的动作ID，逗号分隔", alias="actionIds"
    ),
):
    from chat2rag.models import RobotAction

    if action_ids:
        id_list = [
            int(id.strip()) for id in action_ids.split(",") if id.strip().isdigit()
        ]
        actions = await RobotAction.filter(id__in=id_list).order_by("-id")
    else:
        q = Q()
        if is_active is not None:
            q &= Q(is_active=is_active)
        actions = await RobotAction.filter(q).order_by("-id")

    data = []
    for action in actions:
        data.append(
            {
                "名称": action.name,
                "代码": action.code,
                "是否启用": "是" if action.is_active else "否",
                "描述": action.description or "",
            }
        )

    df = pd.DataFrame(data)

    if format.lower() == "csv":
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding="utf-8-sig")
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=actions.csv"},
        )
    else:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="动作列表")
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=actions.xlsx"},
        )


@router.post("/import", summary="导入动作")
async def import_actions(file: UploadFile = File(...)):
    from chat2rag.models import RobotAction

    if not file.filename:
        return BaseResponse.error(msg="未选择文件")

    filename = file.filename.lower()
    if not (
        filename.endswith(".xlsx")
        or filename.endswith(".xls")
        or filename.endswith(".csv")
    ):
        return BaseResponse.error(msg="只支持 Excel (.xlsx, .xls) 或 CSV 文件")

    try:
        content = await file.read()

        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")
        else:
            df = pd.read_excel(io.BytesIO(content), sheet_name=0)

        df = df.fillna("")

        required_cols = ["名称", "代码"]
        for col in required_cols:
            if col not in df.columns:
                return BaseResponse.error(msg=f"缺少必要列: {col}")

        created_count = 0
        updated_count = 0
        error_count = 0

        for _, row in df.iterrows():
            try:
                name = str(row.get("名称", "")).strip()
                code = str(row.get("代码", "")).strip()

                if not name or not code:
                    error_count += 1
                    continue

                is_active_str = str(row.get("是否启用", "是")).strip()
                is_active = is_active_str in ["是", "true", "1", "yes", "启用"]

                description = str(row.get("描述", "")).strip() or None

                existing = await RobotAction.filter(code=code).first()

                if existing:
                    existing.name = name
                    existing.is_active = is_active
                    existing.description = description
                    await existing.save()
                    updated_count += 1
                else:
                    await RobotAction.create(
                        name=name,
                        code=code,
                        is_active=is_active,
                        description=description,
                    )
                    created_count += 1

            except Exception as e:
                logger.error(f"Failed to import action row: {e}")
                error_count += 1

        return BaseResponse.success(
            msg=f"导入完成: 新增 {created_count} 条, 更新 {updated_count} 条, 失败 {error_count} 条"
        )

    except Exception as e:
        logger.exception(f"Failed to import actions: {e}")
        return BaseResponse.error(msg=f"导入失败: {str(e)}")


@router.get(
    "", response_model=PaginatedResponse[RobotActionData], summary="获取机器人动作列表"
)
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

    total, actions = await robot_action_service.get_list(
        current, size, q, order=["-id"]
    )

    return PaginatedResponse.create(
        items=[RobotActionData.model_validate(action) for action in actions],
        total=total,
        current=current,
        size=size,
    )


@router.get(
    "/{action_id}",
    response_model=BaseResponse[RobotActionData],
    summary="获取机器人动作详情",
)
async def get_robot_action_detail(action_id: int):
    action = await robot_action_service.get(action_id)
    return BaseResponse.success(data=RobotActionData.model_validate(action))


@router.post("", response_model=BaseResponse[RobotActionData], summary="创建机器人动作")
async def create_robot_action(action_in: RobotActionCreate):
    action = await robot_action_service.create(action_in)
    return BaseResponse.success(data=RobotActionData.model_validate(action))


@router.put(
    "/{action_id}",
    response_model=BaseResponse[RobotActionData],
    summary="更新机器人动作",
)
async def update_robot_action(action_id: int, action_in: RobotActionUpdate):
    action = await robot_action_service.update(action_id, action_in)
    return BaseResponse.success(data=RobotActionData.model_validate(action))


@router.delete("/{action_id}", response_model=BaseResponse, summary="删除机器人动作")
async def delete_robot_action(action_id: int):
    await robot_action_service.remove(action_id)
    return BaseResponse.success(msg="删除成功")
