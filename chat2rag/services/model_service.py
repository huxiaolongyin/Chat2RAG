import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from httpx import AsyncClient
from pydantic.main import IncEx
from tortoise.expressions import Q

from chat2rag.config import CONFIG
from chat2rag.core.crud import CRUDBase
from chat2rag.logger import get_logger
from chat2rag.models import ModelLatency, ModelProvider, ModelSource
from chat2rag.schemas.model import (
    ModelProviderCreate,
    ModelProviderUpdate,
    ModelSourceCreate,
    ModelSourceUpdate,
)

logger = get_logger(__name__)


class ModelProviderService(
    CRUDBase[ModelProvider, ModelProviderCreate, ModelProviderUpdate]
):
    def __init__(self):
        super().__init__(ModelProvider)

    async def create(self, obj_in, exclude):
        provider = await super().create(obj_in, exclude)
        if provider.enabled:
            await self.get_models(provider)
        return provider

    async def update(self, id, obj_in, exclude):
        provider = await super().update(id, obj_in, exclude)
        await ModelSource.filter(provider=provider).all().delete()
        if provider.enabled:
            await self.get_models(provider)
        return provider

    async def get_enabled_providers(self) -> List[ModelProvider]:
        """获取所有启用的模型渠道商"""
        return await self.model.filter(enabled=True).all()

    async def get_models(self, provider: ModelProvider):
        """获取模型列表。"""
        url = f"{provider.base_url}/models"
        headers = {}
        headers["Authorization"] = f"Bearer {provider.api_key}"
        async with AsyncClient(timeout=20, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()  # 抛出异常如果状态异常
            json_data = response.json()
        model_source_objs = [
            ModelSource(
                **{"provider": provider, "name": model.get("id"), "enabled": False}
            )
            for model in json_data.get("data", {})
        ]
        if model_source_objs:
            await ModelSource.bulk_create(model_source_objs)


class ModelSourceService(CRUDBase[ModelSource, ModelSourceCreate, ModelSourceUpdate]):
    def __init__(self):
        super().__init__(ModelSource)

    async def update(
        self,
        id,
        obj_in,
        exclude: IncEx = None,
    ):
        source = await super().update(id, obj_in, exclude)
        if source.enabled:
            await self.update_latency(source)
        return source

    async def get_best_source(self, name_or_alias: str) -> Optional[ModelSource]:
        """通过模型别名或名称查询，返回延迟最低且健康的模型源"""
        model_source = (
            await self.model.filter(
                Q(alias__icontains=name_or_alias)
                | Q(name__icontains=name_or_alias)
                | Q(enabled=True)
                | Q(healthy=True)
            )
            .order_by("-priority", "last_latency")
            .first()
        )
        if not model_source:
            logger.warning("The model was not recognized. Select the default model")
            model_source = (
                await self.model.filter(
                    Q(alias__icontains=CONFIG.MODEL) | Q(name__icontains=CONFIG.MODEL)
                )
                .order_by("-priority", "last_latency")
                .first()
            )
        return model_source

    async def update_latency(self, source: ModelSource):
        """更新模型源的延迟和健康状态数据"""
        provider: ModelProvider = await source.provider
        test_result = await test_model_streaming_latency(
            provider.base_url,
            source.name,
            api_key=provider.api_key,
        )
        success = test_result.get("success", False)
        latency_ms = test_result.get("ttfb")
        error_msg = test_result.get("error_message", "")

        if success:
            source.last_latency = latency_ms
            source.last_check_time = datetime.now()
            source.failure_count = 0
            source.healthy = True
        else:
            source.failure_count += 1
            if source.failure_count >= 3:
                source.healthy = False

        await source.save()

        latency_record = ModelLatency(
            model_source_id=source.id,
            latency=latency_ms,
            success=success,
            error_message=error_msg,
        )
        await latency_record.save()

        return source

    async def update_all_enabled_latency(self):
        """遍历所有启用的模型源，更新延迟数据"""
        enabled_sources: List[ModelSource] = await self.model.filter(enabled=True).all()
        for source in enabled_sources:
            await self.update_latency(source)


async def periodic_latency_update(
    service: ModelSourceService, interval_sec: int = 3600
):
    """后台定时任务，loop里每隔 interval_sec 秒调用更新延迟"""
    while True:
        try:
            await service.update_all_enabled_latency()
        except Exception as e:
            logger.error(f"Periodic latency update error: {e}")
        await asyncio.sleep(interval_sec)


async def test_model_streaming_latency(
    base_url: str, model_name: str, api_key: Optional[str] = None, timeout: float = 30.0
) -> Dict[str, Any]:
    """测试流式响应的首字节延迟"""
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "hi"}],
        "stream": True,
        "max_tokens": 10,
    }

    try:
        start_time = time.time()
        first_byte_time = None

        async with AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST", url, json=payload, headers=headers
            ) as response:
                response.raise_for_status()

                # 读取第一块数据
                async for chunk in response.aiter_bytes():
                    if chunk and first_byte_time is None:
                        first_byte_time = time.time()
                        break

                ttfb = (
                    (first_byte_time - start_time) * 1000 if first_byte_time else None
                )

                return {
                    "success": True,
                    "ttfb": round(ttfb, 2) if ttfb else None,  # 首字节延迟（毫秒）
                    "status_code": response.status_code,
                    "error_message": None,
                }

    except Exception as e:
        latency = time.time() - start_time
        return {
            "success": False,
            "ttfb": round(latency * 1000, 2),
            "status_code": None,
            "error_message": str(e),
        }
