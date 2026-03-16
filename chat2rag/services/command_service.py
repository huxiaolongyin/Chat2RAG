from typing import List

from chat2rag.core.crud import CRUDBase
from chat2rag.core.exceptions import BusinessException, ValueAlreadyExist, ValueNoExist
from chat2rag.models import Command, CommandCategory, CommandVariant
from chat2rag.models.command import ParamType
from chat2rag.schemas.command import (
    CommandCategoryCreate,
    CommandCategoryUpdate,
    CommandCreate,
    CommandUpdate,
)


class CommandCategoryService(
    CRUDBase[CommandCategory, CommandCategoryCreate, CommandCategoryUpdate]
):
    def __init__(self):
        super().__init__(CommandCategory)

    async def create(self, obj_in: CommandCategoryCreate, exclude=None):
        if await self.model.filter(name=obj_in.name).exists():
            raise ValueAlreadyExist("该指令分类已存在")
        return await super().create(obj_in, exclude)

    async def update(self, id: int, obj_in: CommandCategoryUpdate, exclude=None):
        await category_service.get(id)
        if (
            obj_in.name
            and await self.model.filter(name=obj_in.name).exclude(id=id).first()
        ):
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

    async def create(
        self, obj_in: CommandCreate, exclude=["commands", "variants"]
    ) -> Command:
        if await self.model.filter(name=obj_in.name).exists():
            raise ValueAlreadyExist("该指令名称已存在")

        if await self.model.filter(code=obj_in.code).exists():
            raise ValueAlreadyExist("该指令代码已存在")

        if (
            obj_in.category_id
            and not await CommandCategory.filter(id=obj_in.category_id).exists()
        ):
            raise ValueNoExist("指定的分类不存在")

        command = await super().create(obj_in, exclude=exclude)

        await self._create_variants(command, obj_in)

        return command

    async def update(
        self, id: int, obj_in: CommandUpdate, exclude=["commands", "variants"]
    ):
        await self.get(id)

        if (
            obj_in.name
            and await self.model.filter(name=obj_in.name).exclude(id=id).exists()
        ):
            raise ValueAlreadyExist("该指令名称已存在")
        if (
            obj_in.code
            and await self.model.filter(code=obj_in.code).exclude(id=id).exists()
        ):
            raise ValueAlreadyExist("该指令代码已存在")
        if (
            obj_in.category_id
            and not await CommandCategory.filter(id=obj_in.category_id).exists()
        ):
            raise ValueNoExist("指定的分类不存在")

        command = await super().update(id, obj_in, exclude)

        if self._should_update_variants(obj_in):
            await CommandVariant.filter(command_id=id).delete()
            await self._create_variants(command, obj_in, is_update=True)

        return command

    def _should_update_variants(self, obj_in) -> bool:
        """检查是否需要更新变体"""
        if hasattr(obj_in, "variants") and obj_in.variants is not None:
            return True
        if hasattr(obj_in, "commands") and obj_in.commands is not None:
            return True
        return False

    async def _create_variants(self, command, obj_in, is_update: bool = False):
        """创建指令变体"""
        if hasattr(obj_in, "variants") and obj_in.variants:
            await self._create_variants_from_list(command, obj_in.variants, is_update)
        elif hasattr(obj_in, "commands") and obj_in.commands:
            await self._create_variants_from_text(command, obj_in.commands, is_update)

    async def _create_variants_from_list(
        self, command, variants: list, is_update: bool = False
    ):
        """从变体列表创建变体"""
        variant_objects = []
        for v in variants:
            text = v.text if hasattr(v, "text") else v.get("text", "")
            pattern = v.pattern if hasattr(v, "pattern") else v.get("pattern")
            if text:
                if is_update:
                    variant_objects.append(
                        CommandVariant(
                            command_id=command.id, text=text.strip(), pattern=pattern
                        )
                    )
                else:
                    variant_objects.append(
                        CommandVariant(
                            command=command, text=text.strip(), pattern=pattern
                        )
                    )

        if variant_objects:
            await CommandVariant.bulk_create(variant_objects)

    async def _create_variants_from_text(
        self, command, commands_text: str, is_update: bool = False
    ):
        """从管道分隔的文本创建变体（向后兼容）"""
        variant_texts = {
            text.strip() for text in commands_text.split("|") if text.strip()
        }

        if variant_texts:
            new_variants = variant_texts
            if not is_update:
                existing = await CommandVariant.filter(
                    command=command, text__in=list(variant_texts)
                ).values_list("text", flat=True)
                existing_set = set(str(v) for v in existing)
                new_variants = variant_texts - existing_set

            if new_variants:
                has_param = (
                    hasattr(command, "param_type")
                    and command.param_type != ParamType.NONE
                )

                if is_update:
                    variant_objects = [
                        CommandVariant(
                            command_id=command.id,
                            text=text,
                            pattern=text if has_param else None,
                        )
                        for text in new_variants
                    ]
                else:
                    variant_objects = [
                        CommandVariant(
                            command=command,
                            text=text,
                            pattern=text if has_param else None,
                        )
                        for text in new_variants
                    ]
                await CommandVariant.bulk_create(variant_objects)


category_service = CommandCategoryService()
command_service = CommandService()
