from typing import Dict, List, Optional

from tortoise.expressions import Q

from chat2rag.core.crud import CRUDBase
from chat2rag.models import Prompt, PromptVersion
from chat2rag.schemas.prompt import PromptCreate, PromptUpdate


class PromptService(CRUDBase[Prompt, PromptCreate, PromptUpdate]):
    def __init__(self):
        super().__init__(Prompt)

    async def create(self, obj_in: PromptCreate):
        """创建提示词"""

        prompt = await self.model.create(prompt_name=obj_in.prompt_name)
        prompt_version = await PromptVersion.create(
            prompt=prompt,
            prompt_desc=obj_in.prompt_desc,
            prompt_text=obj_in.prompt_text,
            version=1,
        )
        prompt.current_version = 1
        await prompt.save(update_fields=["current_version"])
        return {**await prompt.to_dict(), **await prompt_version.to_dict()}

    async def update(self, id: int, obj_in: PromptUpdate):
        """更新提示词"""

        prompt = await self.get(id)
        if not prompt:
            return None
        latest_version_obj = (
            await PromptVersion.filter(prompt=prompt).order_by("-version").first()
        )
        new_version = latest_version_obj.version + 1 if latest_version_obj else 1

        prompt_version = await PromptVersion.create(
            prompt=prompt,
            prompt_desc=obj_in.prompt_desc,
            prompt_text=obj_in.prompt_text,
            version=new_version,
        )
        prompt.current_version = new_version
        await prompt.save(update_fields=["current_version"])

        return {
            **await prompt.to_dict(),
            **await prompt_version.to_dict(
                exclude_fields=[
                    "id",
                    "prompt_id",
                    "create_time",
                    "update_time",
                ]
            ),
        }

    # fmt: off
    async def set_version(self, id: str, version: int | None = None):
        """设定当前使用版本"""
        prompt = await self.get(id)
        if not prompt:
            return None

        if version is None:
            latest_version_obj = await PromptVersion.filter(prompt=prompt).order_by("-version").first()
            if not latest_version_obj:
                return None
            version = latest_version_obj.version

        else:
            version_obj = await PromptVersion.filter(prompt=prompt, version=version).first()
            if not version_obj:
                return None

        prompt.current_version = version
        await prompt.save(update_fields=["current_version"])

        # 返回当前生效版本的数据
        current_version_obj = await PromptVersion.filter(prompt=prompt, version=version).first()

        return {**await prompt.to_dict(), 
                **await current_version_obj.to_dict(
                    exclude_fields=[
                        "id",
                        "prompt_id",
                        "create_time",
                        "update_time",
                ])}
    # fmt: on

    async def remove(self, id: int) -> bool:
        """删除提示词及其所有版本"""

        prompt = await self.get(id)
        if not prompt:
            raise "没有提示词"
        # 先删除版本
        await PromptVersion.filter(prompt=prompt).delete()
        # 再删除提示词
        await prompt.delete()

    async def get_list(
        self,
        page: int,
        page_size: int,
        search: Q = Q(),
        order: list[str] | None = None,
        prefetch: Optional[List[str]] = None,
        distinct: bool = False,
    ) -> List[dict]:
        """列出所有提示词及其当前版本内容，分页支持"""

        total, prompts = await super().get_list(
            page, page_size, search, order, prefetch, distinct
        )
        results = []
        for prompt in prompts:
            current_version = prompt.current_version
            version_obj = None
            if current_version is not None:
                version_obj = await PromptVersion.filter(
                    prompt=prompt, version=current_version
                ).first()
            # 组装返回，版本可能为空
            if version_obj:
                results.append(
                    {
                        **await prompt.to_dict(),
                        **await version_obj.to_dict(
                            exclude_fields=[
                                "id",
                                "prompt_id",
                                "create_time",
                                "update_time",
                            ]
                        ),
                    }
                )
            else:
                results.append(await prompt.to_dict())
        return total, results

    async def get_detail(self, id: int) -> Optional[dict]:
        """
        查询某个提示词详情，包括基本信息、当前版本、所有版本列表
        """
        prompt = await self.get(id)
        if not prompt:
            return None
        versions = await PromptVersion.filter(prompt=prompt).order_by("version").all()
        versions_list = [await v.to_dict() for v in versions]
        current_version_obj = None
        if prompt.current_version is not None:
            current_version_obj = await PromptVersion.filter(
                prompt=prompt, version=prompt.current_version
            ).first()
        return {
            **await prompt.to_dict(),
            "current_version_data": (
                await current_version_obj.to_dict() if current_version_obj else None
            ),
            "versions": versions_list,
        }

    async def get_by_prompt_name(self, prompt_name: str) -> Dict[any, str]:
        prompt = await self.model.filter(prompt_name=prompt_name).first()
        if not prompt:
            return False
        version = prompt.current_version
        if version:
            version_obj = await PromptVersion.filter(
                prompt=prompt, version=version
            ).first()
        else:
            version_obj = (
                await PromptVersion.filter(prompt=prompt).order_by("-version").first()
            )
        return {
            **await prompt.to_dict(),
            **await version_obj.to_dict(
                exclude_fields=[
                    "id",
                    "prompt_id",
                    "create_time",
                    "update_time",
                ]
            ),
        }
