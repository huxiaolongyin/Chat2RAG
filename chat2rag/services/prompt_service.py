from typing import Any, Dict, List, Optional

from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from chat2rag.config import CONFIG
from chat2rag.core.crud import CRUDBase
from chat2rag.exceptions import ValueAlreadyExist, ValueNoExist
from chat2rag.logger import get_logger
from chat2rag.models import Prompt, PromptVersion
from chat2rag.schemas.prompt import PromptCreate, PromptItemResponse, PromptUpdate

logger = get_logger(__name__)


def _merge_prompt_version_data(
    prompt: Prompt, version: PromptVersion
) -> PromptItemResponse:
    """合并提示词和版本数据的公共方法"""
    return PromptItemResponse(
        id=prompt.id,
        prompt_name=prompt.prompt_name,
        current_version=prompt.current_version,
        prompt_text=version.prompt_text,
        prompt_desc=version.prompt_desc,
        version=version.version,
        create_time=prompt.create_time,
        update_time=prompt.update_time,
    )


class PromptService(CRUDBase[Prompt, PromptCreate, PromptUpdate]):
    def __init__(self):
        super().__init__(Prompt)

    async def ensure_default_prompt(self):
        """确保默认提示词存在（仅在启动时调用一次）"""
        default_prompt = await self.model.filter(prompt_name="默认").first()
        if not default_prompt:
            await self.create(
                PromptCreate(
                    promptName="默认",
                    promptDesc="默认提示词",
                    promptText=CONFIG.RAG_PROMPT_TEMPLATE,
                )
            )
            logger.info("已创建默认提示词")

    async def create(self, obj_in: PromptCreate):
        """创建提示词"""

        # 查看是否已存在该名称
        if await self.model.filter(prompt_name=obj_in.prompt_name).exists():
            raise ValueAlreadyExist(msg=f"提示词名称:{obj_in.prompt_name} 已存在")

        # 使用事务确保数据一致性
        async with in_transaction():
            prompt = await self.model.create(prompt_name=obj_in.prompt_name)
            try:
                prompt_version = await PromptVersion.create(
                    prompt=prompt,
                    prompt_desc=obj_in.prompt_desc,
                    prompt_text=obj_in.prompt_text,
                    version=1,
                )
                prompt.current_version = 1
                await prompt.save(update_fields=["current_version"])
            except Exception:
                # 事务会自动回滚
                raise

        return _merge_prompt_version_data(prompt, prompt_version)

    async def update(self, id: int, obj_in: PromptUpdate):
        """更新提示词"""

        # 查看提示词是否不存在
        prompt = await self.get(id)
        if not prompt:
            raise ValueNoExist(f"提示词ID {id} 不存在")

        # 查看是否已存在该名称
        if obj_in.prompt_name:
            exist_prompt = (
                await self.model.filter(prompt_name=obj_in.prompt_name)
                .exclude(id=id)
                .first()
            )
            if exist_prompt:
                raise ValueAlreadyExist(msg=f"提示词名称:{obj_in.prompt_name} 已存在")

        latest_version_obj = (
            await PromptVersion.filter(prompt=prompt).order_by("-version").first()
        )
        new_version = latest_version_obj.version + 1 if latest_version_obj else 1

        # 使用事务确保数据一致性
        async with in_transaction():
            prompt_version = await PromptVersion.create(
                prompt=prompt,
                prompt_desc=obj_in.prompt_desc,
                prompt_text=obj_in.prompt_text,
                version=new_version,
            )
            prompt.current_version = new_version
            await prompt.save(update_fields=["current_version"])

        return _merge_prompt_version_data(prompt, prompt_version)

    async def set_version(
        self, id: int, version: int | None = None
    ) -> PromptItemResponse:
        """设定当前使用版本"""
        prompt = await self.get(id)
        if not prompt:
            raise ValueNoExist(f"提示词ID {id} 不存在")

        if version is None:
            latest_version_obj = (
                await PromptVersion.filter(prompt=prompt).order_by("-version").first()
            )
            if not latest_version_obj:
                raise ValueNoExist(f"版本 {version} 不存在")
            version = latest_version_obj.version

        else:
            version_obj = await PromptVersion.filter(
                prompt=prompt, version=version
            ).first()
            if not version_obj:
                raise ValueNoExist(f"版本 {version} 不存在")

        prompt.current_version = version
        await prompt.save(update_fields=["current_version"])

        # 返回当前生效版本的数据
        current_version_obj = await PromptVersion.filter(
            prompt=prompt, version=version
        ).first()

        return _merge_prompt_version_data(prompt, current_version_obj)

    async def remove(self, id: int) -> bool:
        """删除提示词及其所有版本"""
        prompt = await self.get(id)
        if not prompt:
            raise ValueNoExist(f"提示词ID {id} 不存在")

        async with in_transaction():
            await PromptVersion.filter(prompt=prompt).delete()
            await prompt.delete()

        return True

    async def get_version(self, id: int):
        prompt = await super().get(id)
        if not prompt:
            raise ValueNoExist(f"提示词ID {id} 不存在")
        await prompt.fetch_related("versions")
        version_map = {v.version: v for v in prompt.versions}
        current_version_data = version_map.get(prompt.current_version)

        return _merge_prompt_version_data(prompt, current_version_data)

    async def get_list(
        self,
        page: int,
        page_size: int,
        search: Q = Q(),
        order: list[str] | None = None,
        prefetch: Optional[List[str]] = None,
        distinct: bool = False,
    ) -> tuple[int, List[PromptItemResponse]]:
        """优化后的列表查询"""

        # 使用select_related和prefetch_related优化查询
        queryset = self.model.filter(search)
        if order:
            queryset = queryset.order_by(*order)

        total = await queryset.count()

        # 一次性获取所有需要的数据
        prompts = (
            await queryset.offset((page - 1) * page_size)
            .limit(page_size)
            .prefetch_related("versions")
        )

        results = []
        for prompt in prompts:
            # 直接从预加载的数据中查找当前版本
            current_version_data = next(
                (v for v in prompt.versions if v.version == prompt.current_version),
                None,
            )

            if current_version_data:
                results.append(_merge_prompt_version_data(prompt, current_version_data))

        return total, results

    async def get_by_prompt_name(self, prompt_name: str) -> Dict[str, Any]:
        prompt = await self.model.filter(prompt_name=prompt_name).first()
        if not prompt:
            raise ValueNoExist(msg="提示词不存在")
        version = prompt.current_version
        if version:
            version_obj = await PromptVersion.filter(
                prompt=prompt, version=version
            ).first()
        else:
            version_obj = (
                await PromptVersion.filter(prompt=prompt).order_by("-version").first()
            )
        return _merge_prompt_version_data(prompt, version_obj)


prompt_service = PromptService()
