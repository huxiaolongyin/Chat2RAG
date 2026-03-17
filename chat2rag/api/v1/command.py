import io

import pandas as pd
from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import StreamingResponse
from tortoise.expressions import Q

from chat2rag.core.logger import get_logger
from chat2rag.models import Command, CommandCategory, CommandVariant
from chat2rag.models.command import ParamType
from chat2rag.schemas.base import BaseResponse, PaginatedResponse
from chat2rag.schemas.command import (
    CommandBatchMove,
    CommandCategoryCreate,
    CommandCategoryData,
    CommandCategoryIdData,
    CommandCategoryUpdate,
    CommandCreate,
    CommandData,
    CommandUpdate,
)
from chat2rag.schemas.common import Current, Size
from chat2rag.services.command_service import category_service, command_service

logger = get_logger(__name__)

router = APIRouter()


# ==================== CommandCategory APIs ====================
@router.get(
    "/category",
    response_model=PaginatedResponse[CommandCategoryData],
    summary="获取指令分类列表",
)
async def get_command_category_list(
    current: Current = 1,
    size: Size = 10,
    name_or_desc: str = Query(None, description="名称或描述", alias="nameOrDesc", max_length=50),
):
    q = Q()
    if name_or_desc:
        q &= Q(name__icontains=name_or_desc) | Q(description__icontains=name_or_desc)

    total, categories = await category_service.get_list(current, size, q)

    return PaginatedResponse.create(
        items=[CommandCategoryData.model_validate(item) for item in categories],
        total=total,
        current=current,
        size=size,
    )


@router.get(
    "/category/{category_id}",
    response_model=BaseResponse[CommandCategoryData],
    summary="获取指令分类详情",
)
async def get_command_category_detail(category_id: int):
    category = await category_service.get(category_id)
    return BaseResponse.success(data=CommandCategoryData.model_validate(category))


@router.post("/category", response_model=BaseResponse, summary="创建指令分类")
async def create_command_category(category_in: CommandCategoryCreate):
    category = await category_service.create(category_in)
    return BaseResponse.success(data=CommandCategoryData.model_validate(category))


@router.put(
    "/category/{category_id}",
    response_model=BaseResponse[CommandCategoryIdData],
    summary="更新指令分类",
)
async def update_command_category(category_id: int, category_in: CommandCategoryUpdate):
    category = await category_service.update(category_id, category_in)
    return BaseResponse.success(data=CommandCategoryIdData(category_id=category.id), msg="更新指令分类成功")


@router.delete("/category/{category_id}", response_model=BaseResponse, summary="删除指令分类")
async def delete_command_category(category_id: int):
    await category_service.remove(category_id)
    return BaseResponse.success(msg="删除成功")


# ==================== Command APIs ====================
@router.get("", response_model=PaginatedResponse[CommandData], summary="获取指令列表")
async def get_command_list(
    current: Current = 1,
    size: Size = 10,
    keyword: str = Query(None, description="指令名称或代码", max_length=50),
    category_id: int = Query(None, description="分类ID", alias="categoryId"),
    is_active: bool = Query(None, description="是否启用", alias="isActive"),
):
    q = Q()
    if keyword:
        q &= Q(name__icontains=keyword) | Q(code__icontains=keyword)
    if category_id is not None:
        if category_id == -1:
            q &= Q(category_id=None)
        elif category_id > 0:
            q &= Q(category_id=category_id)
    if is_active is not None:
        q &= Q(is_active=is_active)

    total, commands = await command_service.get_list(
        current,
        size,
        q,
        prefetch=["category", "variants"],
        order=["-priority", "-id"],
    )

    # 获取所有变体指令
    commandList = []
    for command in commands:
        variants = await command.variants.all()
        variant_texts = "|".join([variant.text for variant in variants])
        data = await command.to_dict()
        data["commands"] = variant_texts
        commandList.append(data)
    return PaginatedResponse.create(
        items=[CommandData.model_validate(c) for c in commandList],
        total=total,
        current=current,
        size=size,
    )


@router.get("/template", summary="下载命令导入模板")
async def download_template():
    data = [
        {
            "名称": "向左转",
            "代码": "TurnLeft",
            "命令词": "左转|向左转|左边转",
            "回复内容": "好的，正在向左转",
            "分类": "移动控制",
            "优先级": 10,
            "参数类型": "none",
            "是否启用": "是",
            "描述": "控制机器人向左转",
            "示例": "左转|向左转一下",
        },
        {
            "名称": "音量调整",
            "代码": "SetVolume",
            "命令词": "音量|声音大小|调节音量",
            "回复内容": "",
            "分类": "系统控制",
            "优先级": 5,
            "参数类型": "number",
            "是否启用": "是",
            "描述": "调整系统音量",
            "示例": "音量调到50|声音大一点",
        },
    ]

    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="命令模板")
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=command_template.xlsx"},
    )


@router.get("/export", summary="导出命令")
async def export_commands(
    format: str = Query("xlsx", description="导出格式: xlsx 或 csv"),
    category_id: int = Query(None, description="分类ID", alias="categoryId"),
    is_active: bool = Query(None, description="是否启用", alias="isActive"),
    command_ids: str = Query(None, description="选中的命令ID，逗号分隔", alias="commandIds"),
):
    if command_ids:
        id_list = [int(id.strip()) for id in command_ids.split(",") if id.strip().isdigit()]
        commands = (
            await Command.filter(id__in=id_list).prefetch_related("category", "variants").order_by("-priority", "-id")
        )
    else:
        q = Q()
        if category_id is not None:
            if category_id == -1:
                q &= Q(category_id=None)
            elif category_id > 0:
                q &= Q(category_id=category_id)
        if is_active is not None:
            q &= Q(is_active=is_active)
        commands = await Command.filter(q).prefetch_related("category", "variants").order_by("-priority", "-id")

    categories_map = {}
    async for c in CommandCategory.all():
        categories_map[c.id] = c.name

    data = []
    for cmd in commands:
        variants = await cmd.variants.all()
        variant_texts = "|".join([v.text for v in variants])
        examples_text = "|".join(cmd.examples) if cmd.examples else ""
        category_name = categories_map.get(cmd.category_id, "") if cmd.category_id else ""

        data.append(
            {
                "名称": cmd.name,
                "代码": cmd.code,
                "命令词": variant_texts,
                "回复内容": cmd.reply or "",
                "分类": category_name,
                "优先级": cmd.priority,
                "参数类型": cmd.param_type,
                "是否启用": "是" if cmd.is_active else "否",
                "描述": cmd.description or "",
                "示例": examples_text,
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
            headers={"Content-Disposition": "attachment; filename=commands.csv"},
        )
    else:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="命令列表")
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=commands.xlsx"},
        )


@router.post("/import", summary="导入命令")
async def import_commands(file: UploadFile = File(...)):
    if not file.filename:
        return BaseResponse.error(msg="未选择文件")

    filename = file.filename.lower()
    if not (filename.endswith(".xlsx") or filename.endswith(".xls") or filename.endswith(".csv")):
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

        categories_map = {c.name: c.id async for c in category_service.model.all()}

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

                category_name = str(row.get("分类", "")).strip()
                category_id = categories_map.get(category_name) if category_name else None

                commands_text = str(row.get("命令词", "")).strip()
                commands_list = [c.strip() for c in commands_text.split("|") if c.strip()] if commands_text else []

                examples_text = str(row.get("示例", "")).strip()
                examples_list = [e.strip() for e in examples_text.split("|") if e.strip()] if examples_text else []

                param_type_str = str(row.get("参数类型", "none")).strip().lower()
                param_type = ParamType.NONE
                if param_type_str in ["number", "数字"]:
                    param_type = ParamType.NUMBER
                elif param_type_str in ["text", "文本"]:
                    param_type = ParamType.TEXT

                is_active_str = str(row.get("是否启用", "是")).strip()
                is_active = is_active_str in ["是", "true", "1", "yes", "启用"]

                priority = 0
                try:
                    priority = int(float(row.get("优先级") or 0))
                except (ValueError, TypeError):
                    priority = 0

                reply = str(row.get("回复内容", "")).strip() or None
                description = str(row.get("描述", "")).strip() or None

                existing = await Command.filter(code=code).first()

                if existing:
                    existing.name = name
                    existing.category_id = category_id
                    existing.priority = priority
                    existing.param_type = param_type
                    existing.is_active = is_active
                    existing.reply = reply
                    existing.description = description
                    existing.examples = examples_list
                    await existing.save()

                    await CommandVariant.filter(command_id=existing.id).delete()
                    for cmd_text in commands_list:
                        await CommandVariant.create(command_id=existing.id, text=cmd_text)

                    updated_count += 1
                else:
                    cmd_create = CommandCreate(
                        name=name,
                        code=code,
                        reply=reply,
                        category_id=category_id,
                        priority=priority,
                        description=description,
                        is_active=is_active,
                        commands="|".join(commands_list) if commands_list else None,
                        param_type=param_type,
                        examples=examples_list if examples_list else [],
                    )
                    await command_service.create(cmd_create)
                    created_count += 1

            except Exception as e:
                logger.error(f"Failed to import command row: {e}")
                error_count += 1

        return BaseResponse.success(
            msg=f"导入完成: 新增 {created_count} 条, 更新 {updated_count} 条, 失败 {error_count} 条"
        )

    except Exception as e:
        logger.exception(f"Failed to import commands: {e}")
        return BaseResponse.error(msg=f"导入失败: {str(e)}")


@router.get("/{command_id}", response_model=BaseResponse[CommandData], summary="获取指令详情")
async def get_command_detail(command_id: int):
    command = await command_service.get(command_id)

    # 获取所有变体指令
    variants = await command.variants.all()
    variant_texts = "|".join([variant.text for variant in variants])
    data = await command.to_dict()
    data["commands"] = variant_texts

    return BaseResponse.success(data=CommandData.model_validate(data))


@router.post("", response_model=BaseResponse[CommandData], summary="创建指令")
async def create_command(command_in: CommandCreate):
    command = await command_service.create(command_in)
    command_dict = {**command.__dict__, "commands": command_in.commands}
    return BaseResponse.success(data=CommandData.model_validate(command_dict))


@router.put("/batch-move", response_model=BaseResponse, summary="批量移动命令到指定分类")
async def batch_move_commands(data: CommandBatchMove):
    from chat2rag.models import Command

    if not data.command_ids:
        return BaseResponse.error(msg="请选择要移动的命令")

    count = await Command.filter(id__in=data.command_ids).update(category_id=data.category_id)
    return BaseResponse.success(msg=f"成功移动 {count} 个命令")


@router.put("/{command_id}", response_model=BaseResponse[CommandData], summary="更新指令")
async def update_command(command_id: int, command_in: CommandUpdate):
    command = await command_service.update(command_id, command_in)
    command_dict = {**command.__dict__, "commands": command_in.commands}
    return BaseResponse.success(data=CommandData.model_validate(command_dict))


@router.delete("/{command_id}", response_model=BaseResponse, summary="删除指令")
async def delete_command(command_id: int):
    await command_service.remove(command_id)
    return BaseResponse.success(msg="删除成功")
