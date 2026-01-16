from typing import List

from chat2rag.core.crud import CRUDBase
from chat2rag.core.exceptions import BusinessException, ValueAlreadyExist, ValueNoExist
from chat2rag.models import Command, CommandCategory, CommandVariant
from chat2rag.schemas.command import (
    CommandCategoryCreate,
    CommandCategoryUpdate,
    CommandCreate,
    CommandUpdate,
)


class CommandCategoryService(CRUDBase[CommandCategory, CommandCategoryCreate, CommandCategoryUpdate]):
    def __init__(self):
        super().__init__(CommandCategory)

    async def create(self, obj_in: CommandCategoryCreate, exclude=None):
        if await self.model.filter(name=obj_in.name).exists():
            raise ValueAlreadyExist("该指令分类已存在")
        return await super().create(obj_in, exclude)

    async def update(self, id: int, obj_in: CommandCategoryUpdate, exclude=None):
        await category_service.get(id)
        if obj_in.name and await self.model.filter(name=obj_in.name).exclude(id=id).first():
            raise ValueAlreadyExist("该指令分类名称已存在")
        return await super().update(id, obj_in, exclude)

    async def remove(self, id: int):
        command_count = await Command.filter(category_id=id).count()
        if command_count > 0:
            raise BusinessException(f"该分类下还有 {command_count} 个指令，无法删除")
        return await super().remove(id)

    async def get_active_categories(self) -> List[CommandCategory]:
        """获取所有启用的分类"""
        return await self.model.filter(is_active=True).all()


class CommandService(CRUDBase[Command, CommandCreate, CommandUpdate]):
    def __init__(self):
        super().__init__(Command)

    async def create(self, obj_in: CommandCreate, exclude=["commands"]) -> Command:

        # 检查名称、代码、分类是否已存在
        if await self.model.filter(name=obj_in.name).exists():
            raise ValueAlreadyExist("该指令名称已存在")

        if await self.model.filter(code=obj_in.code).exists():
            raise ValueAlreadyExist("该指令代码已存在")

        if obj_in.category_id and not await CommandCategory.filter(id=obj_in.category_id).exists():
            raise ValueNoExist("指定的分类不存在")

        command = await super().create(obj_in, exclude=exclude)
        commands_text = obj_in.commands

        if not commands_text:
            return command

        # 使用集合去重，同时过滤空字符串和空白字符
        variant_texts = {text.strip() for text in commands_text.split("|") if text.strip()}

        # 避免重复创建相同的变体
        if variant_texts:
            # 检查已存在的变体
            existing_variants = await CommandVariant.filter(command=command, text__in=list(variant_texts)).values_list(
                "text", flat=True
            )

            # 只创建不存在的变体
            new_variants = variant_texts - set(existing_variants)

            if new_variants:
                variant_objects = [CommandVariant(command=command, text=text) for text in new_variants]
                await CommandVariant.bulk_create(variant_objects)

        return command

    async def update(self, id: int, obj_in: CommandUpdate, exclude=["commands"]):
        await self.get(id)

        # 检查名称、代码、分类是否已被其他指令使用
        if obj_in.name and await self.model.filter(name=obj_in.name).exclude(id=id).exists():
            raise ValueAlreadyExist("该指令名称已存在")
        if obj_in.code and await self.model.filter(code=obj_in.code).exclude(id=id).exists():
            raise ValueAlreadyExist("该指令代码已存在")
        if obj_in.category_id and not await CommandCategory.filter(id=obj_in.category_id).exists():
            raise ValueNoExist("指定的分类不存在")

        command = await super().update(id, obj_in, exclude)

        # 如果包含commands字段，则更新变体
        if hasattr(obj_in, "commands") and obj_in.commands is not None:
            commands_text = obj_in.commands

            # 删除现有的变体
            await CommandVariant.filter(command_id=id).delete()

            # 重新创建变体
            if commands_text:
                # 去重并过滤空字符串
                variant_texts = {text.strip() for text in commands_text.split("|") if text.strip()}

                if variant_texts:
                    variant_objects = [CommandVariant(command_id=id, text=text) for text in variant_texts]
                    await CommandVariant.bulk_create(variant_objects)

        return command


category_service = CommandCategoryService()
command_service = CommandService()
