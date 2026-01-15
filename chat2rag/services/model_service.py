import asyncio
from typing import List

from pydantic.main import IncEx
from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from chat2rag.config import CONFIG
from chat2rag.core.crud import CRUDBase
from chat2rag.exceptions import ValueAlreadyExist, ValueNoExist
from chat2rag.logger import get_logger
from chat2rag.models import ModelProvider, ModelSource
from chat2rag.schemas.model import (
    ModelProviderCreate,
    ModelProviderUpdate,
    ModelSourceCreate,
    ModelSourceUpdate,
)

logger = get_logger(__name__)


class ModelProviderService(CRUDBase[ModelProvider, ModelProviderCreate, ModelProviderUpdate]):
    def __init__(self):
        super().__init__(ModelProvider)

    async def create(self, obj_in: ModelProviderCreate, exclude=None) -> ModelProvider:
        """创建模型渠道商"""
        if await model_provider_service.model.filter(name=obj_in.name).exists():
            raise ValueAlreadyExist("该模型渠道商名称已存在")

        return await super().create(obj_in, exclude)

    async def update(self, id: int, obj_in: ModelProviderUpdate, exclude=None) -> ModelProvider:
        """更新模型渠道商"""
        # 名称检查
        if await model_provider_service.model.filter(name=obj_in.name).exclude(id=id).exists():
            raise ValueAlreadyExist("该模型渠道商名称已存在")

        # 使用事务确保数据一致性
        async with in_transaction():
            provider = await super().update(id, obj_in, exclude)
            await ModelSource.filter(provider=provider).all().delete()

        return provider


class ModelSourceService(CRUDBase[ModelSource, ModelSourceCreate, ModelSourceUpdate]):
    def __init__(self):
        super().__init__(ModelSource)

    async def create(self, obj_in, exclude=None):

        if not await ModelProvider.filter(id=obj_in.provider_id).exists():
            raise ValueNoExist("该模型渠道商不存在")

        if await self.model.filter(name=obj_in.name, provider_id=obj_in.provider_id).exists():
            raise ValueAlreadyExist("该模型名称已存在")

        return await super().create(obj_in, exclude)

    async def update(self, id: int, obj_in: ModelSourceUpdate, exclude: IncEx = None) -> ModelSource:
        source = await self.get(id)
        await source.fetch_related("provider")
        if await self.model.filter(name=obj_in.name, provider_id=source.provider.id).exists():
            raise ValueAlreadyExist("该模型名称已存在")

        return await super().update(id, obj_in, exclude)

    async def get_best_source(self, name_or_alias: str, extra_log: str = "") -> ModelSource | None:
        """通过模型别名或名称查询，返回延迟最低且健康的模型源"""
        model_source = (
            await self.model.filter(
                (Q(alias__icontains=name_or_alias) | Q(name__icontains=name_or_alias))
                & Q(enabled=True)
                & Q(healthy=True)
            )
            .order_by("-priority", "last_latency")
            .first()
        )
        if not model_source:
            logger.warning("The model was not recognized. Select the default model")
            model_source = (
                await self.model.filter(Q(alias__icontains=CONFIG.MODEL) | Q(name__icontains=CONFIG.MODEL))
                .order_by("-priority", "last_latency")
                .first()
            )
        provider = await model_source.provider
        logger.info(f"{extra_log} Select model: {provider.name}-{model_source.name}")
        return model_source

    # async def update_latency(self, source: ModelSource):
    #     """更新模型源的延迟和健康状态数据"""
    #     provider: ModelProvider = await source.provider
    #     test_result = await test_model_streaming_latency(
    #         provider.base_url,
    #         source.name,
    #         api_key=provider.api_key,
    #     )
    #     success = test_result.get("success", False)
    #     latency_ms = test_result.get("ttfb")
    #     error_msg = test_result.get("error_message", "")

    #     if success:
    #         source.last_latency = latency_ms
    #         source.last_check_time = datetime.now()
    #         source.failure_count = 0
    #         source.healthy = True
    #     else:
    #         source.failure_count += 1
    #         if source.failure_count >= 3:
    #             source.healthy = False

    #     await source.save()

    #     latency_record = ModelLatency(
    #         model_source_id=source.id,
    #         latency=latency_ms,
    #         success=success,
    #         error_message=error_msg,
    #     )
    #     await latency_record.save()

    #     return source

    async def update_all_enabled_latency(self):
        """遍历所有启用的模型源，更新延迟数据"""
        enabled_sources: List[ModelSource] = await self.model.filter(enabled=True).all()
        for source in enabled_sources:
            await source.update_latency()


async def periodic_latency_update(service: ModelSourceService, interval_sec: int = 3600):
    """后台定时任务，loop里每隔 interval_sec 秒调用更新延迟"""
    while True:
        try:
            await service.update_all_enabled_latency()
        except Exception as e:
            logger.error(f"Periodic latency update error: {e}")
        await asyncio.sleep(interval_sec)


model_provider_service = ModelProviderService()
model_source_service = ModelSourceService()
