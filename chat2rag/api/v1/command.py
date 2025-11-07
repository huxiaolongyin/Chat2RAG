from fastapi import APIRouter, Query
from tortoise.expressions import Q

from chat2rag.logger import auto_log, get_logger
from chat2rag.responses import Error, Success
from chat2rag.schemas.command import (
    CommandCategoryCreate,
    CommandCategoryUpdate,
    CommandCreate,
    CommandUpdate,
)
from chat2rag.schemas.common import Current, Size
from chat2rag.services.command_service import CommandCategoryService, CommandService

logger = get_logger(__name__)

router = APIRouter()

category_service = CommandCategoryService()
command_service = CommandService()


# ==================== CommandCategory APIs ====================
@router.get("/category", summary="获取指令分类列表")
@auto_log(level="info")
async def get_command_category_list(
    current: Current = 1,
    size: Size = 10,
    name_or_desc: str = Query(
        None, description="名称或描述", alias="nameOrDesc", max_length=50
    ),
):
    try:
        q = Q()
        if name_or_desc:
            q &= Q(name__icontains=name_or_desc) | Q(
                description__icontains=name_or_desc
            )

        total, categories = await category_service.get_list(current, size, q)

        return Success(
            data={
                "categoryList": [await category.to_dict() for category in categories],
                "total": total,
                "current": current,
                "size": size,
            }
        )

    except Exception as e:
        msg = f"获取指令分类列表失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.get("/category/{category_id}", summary="获取指令分类详情")
@auto_log(level="info")
async def get_command_category_detail(category_id: int):
    try:
        category = await category_service.get(category_id)

        # 查看是否存在分类
        if not category:
            msg = "指令分类不存在"
            logger.warning(msg)
            return Error(msg)

        return Success(data=await category.to_dict())

    except Exception as e:
        msg = f"获取指令分类详情失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.post("/category", summary="创建指令分类")
@auto_log(level="info")
async def create_command_category(category_in: CommandCategoryCreate):
    try:
        exist_category = await category_service.model.filter(
            name=category_in.name
        ).first()

        # 查看是否重名
        if exist_category:
            msg = "该指令分类已存在"
            logger.warning(msg)
            return Error(msg)

        category = await category_service.create(category_in)
        return Success(data=await category.to_dict())

    except Exception as e:
        msg = f"创建指令分类失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.put("/category/{category_id}", summary="更新指令分类")
@auto_log(level="info")
async def update_command_category(category_id: int, category_in: CommandCategoryUpdate):
    try:
        # 查看是否存在分类
        category = await category_service.get(category_id)
        if not category:
            msg = "指令分类不存在"
            logger.warning(msg)
            return Error(msg)

        if category_in.name:
            # 查看是否重名
            exist_category = (
                await category_service.model.filter(name=category_in.name)
                .exclude(id=category_id)
                .first()
            )
            if exist_category:
                msg = "该指令分类已存在"
                logger.warning(msg)
                return Error(msg)

        category = await category_service.update(category_id, category_in)
        return Success(data={"categoryId": category.id}, msg="更新指令分类成功")

    except Exception as e:
        msg = f"更新指令分类失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.delete("/category/{category_id}", summary="删除指令分类")
@auto_log(level="info")
async def delete_command_category(category_id: int):
    try:
        # 查看是否存在分类
        category = await category_service.get(category_id)
        if not category:
            msg = "指令分类不存在"
            logger.warning(msg)
            return Error(msg)

        # 检查是否有关联的指令
        command_count = await command_service.model.filter(
            category_id=category_id
        ).count()
        if command_count > 0:
            msg = f"该分类下还有 {command_count} 个指令，无法删除"
            logger.warning(msg)
            return Error(msg)

        await category_service.remove(category_id)
        return Success(msg="删除成功")

    except Exception as e:
        msg = f"删除指令分类失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


# ==================== Command APIs ====================
@router.get("/", summary="获取指令列表")
@auto_log(level="info")
async def get_command_list(
    current: Current = 1,
    size: Size = 10,
    keyword: str = Query(None, description="指令名称或代码", max_length=50),
    category_id: int = Query(None, description="分类ID", alias="categoryId"),
    is_active: bool = Query(None, description="是否启用", alias="isActive"),
):
    try:
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

        return Success(
            data={
                "commandList": commandList,
                "total": total,
                "current": current,
                "size": size,
            }
        )
    except Exception as e:
        msg = f"获取指令列表失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.get("/{command_id}", summary="获取指令详情")
@auto_log(level="info")
async def get_command_detail(command_id: int):
    try:
        command = await command_service.get(command_id)
        if not command:
            return Error(msg="指令不存在")

        # 获取所有变体指令
        variants = await command.variants.all()
        variant_texts = "|".join([variant.text for variant in variants])
        data = await command.to_dict()
        data["commands"] = variant_texts

        return Success(data=data)

    except Exception as e:
        msg = f"获取指令详情失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.post("/", summary="创建指令")
@auto_log(level="info")
async def create_command(command_in: CommandCreate):
    try:
        # 检查指令名称是否已存在
        exist_name = await command_service.model.filter(name=command_in.name).first()
        if exist_name:
            return Error(msg="该指令名称已存在")

        # 检查指令代码是否已存在
        exist_code = await command_service.model.filter(code=command_in.code).first()
        if exist_code:
            return Error(msg="该指令代码已存在")

        # 如果指定了分类，检查分类是否存在
        if command_in.category_id:
            category = await category_service.get(command_in.category_id)
            if not category:
                return Error(msg="指定的分类不存在")

        command = await command_service.create(command_in)
        return Success(data=await command.to_dict())

    except Exception as e:
        msg = f"创建指令失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.put("/{command_id}", summary="更新指令")
@auto_log(level="info")
async def update_command(command_id: int, command_in: CommandUpdate):
    try:
        command = await command_service.get(command_id)
        if not command:
            return Error(msg="指令不存在")

        # 检查指令名称是否已被其他指令使用
        if command_in.name:
            exist_name = (
                await command_service.model.filter(name=command_in.name)
                .exclude(id=command_id)
                .first()
            )
            if exist_name:
                return Error(msg="该指令名称已存在")

        # 检查指令代码是否已被其他指令使用
        if command_in.code:
            exist_code = (
                await command_service.model.filter(code=command_in.code)
                .exclude(id=command_id)
                .first()
            )
            if exist_code:
                return Error(msg="该指令代码已存在")

        # 如果更新分类，检查分类是否存在
        if command_in.category_id:
            category = await category_service.get(command_in.category_id)
            if not category:
                return Error(msg="指定的分类不存在")

        command = await command_service.update(command_id, command_in)
        return Success(data=await command.to_dict())

    except Exception as e:
        msg = f"更新指令失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.delete("/{command_id}", summary="删除指令")
@auto_log(level="info")
async def delete_command(command_id: int):
    try:
        command = await command_service.get(command_id)
        if not command:
            return Error(msg="指令不存在")

        # 删除指令时会级联删除关联的变体（因为模型中设置了 on_delete=CASCADE）
        await command_service.remove(command_id)
        return Success(msg="删除成功")

    except Exception as e:
        msg = f"删除指令失败: {str(e)}"
        logger.error(msg)
        return Error(msg)
