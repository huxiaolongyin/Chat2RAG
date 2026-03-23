import io

import pandas as pd
from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import StreamingResponse
from tortoise.expressions import Q

from chat2rag.core.logger import get_logger
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


@router.get("/template", summary="下载表情导入模板")
async def download_template():
    data = [
        {
            "名称": "开心",
            "代码": "Happy",
            "是否启用": "是",
            "描述": "表示开心愉悦的表情",
        },
        {
            "名称": "疑惑",
            "代码": "Confused",
            "是否启用": "是",
            "描述": "表示疑惑不解的表情",
        },
    ]

    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="表情模板")
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=expression_template.xlsx"
        },
    )


@router.get("/export", summary="导出表情")
async def export_expressions(
    format: str = Query("xlsx", description="导出格式: xlsx 或 csv"),
    is_active: bool = Query(None, description="是否启用", alias="isActive"),
    expression_ids: str = Query(
        None, description="选中的表情ID，逗号分隔", alias="expressionIds"
    ),
):
    from chat2rag.models import RobotExpression

    if expression_ids:
        id_list = [
            int(id.strip()) for id in expression_ids.split(",") if id.strip().isdigit()
        ]
        expressions = await RobotExpression.filter(id__in=id_list).order_by("-id")
    else:
        q = Q()
        if is_active is not None:
            q &= Q(is_active=is_active)
        expressions = await RobotExpression.filter(q).order_by("-id")

    data = []
    for expression in expressions:
        data.append(
            {
                "名称": expression.name,
                "代码": expression.code,
                "是否启用": "是" if expression.is_active else "否",
                "描述": expression.description or "",
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
            headers={"Content-Disposition": "attachment; filename=expressions.csv"},
        )
    else:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="表情列表")
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=expressions.xlsx"},
        )


@router.post("/import", summary="导入表情")
async def import_expressions(file: UploadFile = File(...)):
    from chat2rag.models import RobotExpression

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

                existing = await RobotExpression.filter(code=code).first()

                if existing:
                    existing.name = name
                    existing.is_active = is_active
                    existing.description = description
                    await existing.save()
                    updated_count += 1
                else:
                    await RobotExpression.create(
                        name=name,
                        code=code,
                        is_active=is_active,
                        description=description,
                    )
                    created_count += 1

            except Exception as e:
                logger.error(f"Failed to import expression row: {e}")
                error_count += 1

        return BaseResponse.success(
            msg=f"导入完成: 新增 {created_count} 条, 更新 {updated_count} 条, 失败 {error_count} 条"
        )

    except Exception as e:
        logger.exception(f"Failed to import expressions: {e}")
        return BaseResponse.error(msg=f"导入失败: {str(e)}")


@router.get(
    "",
    response_model=PaginatedResponse[RobotExpressionData],
    summary="获取机器人表情列表",
)
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

    total, expressions = await robot_expression_service.get_list(
        current, size, q, order=["-id"]
    )

    return PaginatedResponse.create(
        items=[
            RobotExpressionData.model_validate(expression) for expression in expressions
        ],
        total=total,
        current=current,
        size=size,
    )


@router.get(
    "/{expression_id}",
    response_model=BaseResponse[RobotExpressionData],
    summary="获取机器人表情详情",
)
async def get_robot_expression_detail(expression_id: int):
    expression = await robot_expression_service.get(expression_id)
    return BaseResponse.success(data=RobotExpressionData.model_validate(expression))


@router.post(
    "", response_model=BaseResponse[RobotExpressionData], summary="创建机器人表情"
)
async def create_robot_expression(expression_in: RobotExpressionCreate):
    expression = await robot_expression_service.create(expression_in)
    return BaseResponse.success(data=RobotExpressionData.model_validate(expression))


@router.put(
    "/{expression_id}",
    response_model=BaseResponse[RobotExpressionData],
    summary="更新机器人表情",
)
async def update_robot_expression(
    expression_id: int, expression_in: RobotExpressionUpdate
):
    expression = await robot_expression_service.update(expression_id, expression_in)
    return BaseResponse.success(data=RobotExpressionData.model_validate(expression))


@router.delete(
    "/{expression_id}", response_model=BaseResponse, summary="删除机器人表情"
)
async def delete_robot_expression(expression_id: int):
    await robot_expression_service.remove(expression_id)
    return BaseResponse.success(msg="删除成功")
