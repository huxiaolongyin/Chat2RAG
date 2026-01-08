from fastapi import APIRouter, Query
from tortoise.expressions import Q

from chat2rag.logger import get_logger
from chat2rag.schemas.base import BaseResponse, PaginatedResponse
from chat2rag.schemas.command import (
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
@router.get("/category", response_model=PaginatedResponse[CommandCategoryData], summary="获取指令分类列表")
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
        items=[CommandCategoryData.model_validate(item) for item in categories], total=total, current=current, size=size
    )


@router.get("/category/{category_id}", response_model=BaseResponse[CommandCategoryData], summary="获取指令分类详情")
async def get_command_category_detail(category_id: int):
    category = await category_service.get(category_id)
    return BaseResponse.success(data=CommandCategoryData.model_validate(category))


@router.post("/category", response_model=BaseResponse, summary="创建指令分类")
async def create_command_category(category_in: CommandCategoryCreate):
    category = await category_service.create(category_in)
    return BaseResponse.success(data=CommandCategoryData.model_validate(category))


@router.put("/category/{category_id}", response_model=BaseResponse[CommandCategoryIdData], summary="更新指令分类")
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
    if category_id:
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
        items=[CommandData.model_validate(c) for c in commandList], total=total, current=current, size=size
    )


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
    return BaseResponse.success(data=CommandData.model_validate(command))


@router.put("/{command_id}", response_model=BaseResponse[CommandData], summary="更新指令")
async def update_command(command_id: int, command_in: CommandUpdate):
    command = await command_service.update(command_id, command_in)
    return BaseResponse.success(data=CommandData.model_validate(command))


@router.delete("/{command_id}", response_model=BaseResponse, summary="删除指令")
async def delete_command(command_id: int):
    await command_service.remove(command_id)
    return BaseResponse.success(msg="删除成功")
