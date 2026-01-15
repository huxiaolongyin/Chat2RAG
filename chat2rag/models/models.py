import time
from datetime import datetime
from typing import Any, Dict

from httpx import AsyncClient, ConnectTimeout
from tortoise import fields

from chat2rag.core.logger import get_logger

from .base import BaseModel, TimestampMixin

logger = get_logger(__name__)


async def test_model_streaming_latency(
    base_url: str, model_name: str, api_key: str | None = None, timeout: float = 30.0
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
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()

                # 读取第一块数据
                async for chunk in response.aiter_bytes():
                    if chunk and first_byte_time is None:
                        first_byte_time = time.time()
                        break

                ttfb = (first_byte_time - start_time) * 1000 if first_byte_time else None

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


class ModelProvider(BaseModel, TimestampMixin):
    """模型渠道商"""

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100, unique=True, description="渠道商名称，如OpenAI、Azure、Anthropic")
    base_url = fields.TextField(null=True, description="渠道商默认API地址")
    api_key = fields.TextField(description="调用API密钥或令牌")
    enabled = fields.BooleanField(default=True, description="渠道商是否启用")
    description = fields.TextField(null=True, description="渠道商描述")

    class Meta:
        table = "model_providers"

    async def get_models(self) -> None:
        """同步模型列表到本地"""
        try:
            url = f"{self.base_url}/models"
            headers = {}
            headers["Authorization"] = f"Bearer {self.api_key}"
            async with AsyncClient(timeout=20, headers=headers) as client:
                response = await client.get(url)
                response.raise_for_status()  # 抛出异常如果状态异常
                json_data = response.json()
            model_source_objs = [
                ModelSource(**{"provider": self, "name": model.get("id"), "enabled": False})
                for model in json_data.get("data", {})
            ]
            if model_source_objs:
                await ModelSource.bulk_create(model_source_objs)

        except ConnectTimeout:
            logger.error(f"{self.base_url}连接超时")

        except Exception as e:
            logger.error(f"模型渠道商: {self.name} 列表同步失败")


class ModelSource(BaseModel, TimestampMixin):
    """模型源"""

    id = fields.IntField(primary_key=True)
    provider = fields.ForeignKeyField(
        "app_system.ModelProvider", related_name="sources", on_delete=fields.CASCADE, description="所属渠道商"
    )
    name = fields.CharField(max_length=100)
    alias = fields.CharField(max_length=100, null=True)
    enabled = fields.BooleanField(default=False)
    last_latency = fields.FloatField(null=True, description="最近一次检测的延迟，秒")
    last_check_time = fields.DatetimeField(null=True, description="最近一次延迟检测时间")
    healthy = fields.BooleanField(default=False, description="是否健康可用")
    failure_count = fields.IntField(default=0, description="连续调用失败次数")
    priority = fields.IntField(default=0, description="优先级，数值越大优先级越高")
    generation_kwargs = fields.JSONField(null=True)

    class Meta:
        table = "model_sources"

    async def update_latency(self) -> "ModelSource":
        """更新模型源的延迟和健康状态数据"""
        provider: ModelProvider = await self.provider
        test_result = await test_model_streaming_latency(
            provider.base_url,
            self.name,
            api_key=provider.api_key,
        )
        success = test_result.get("success", False)
        latency_ms = test_result.get("ttfb")
        error_msg = test_result.get("error_message", "")

        if success:
            self.last_latency = latency_ms
            self.last_check_time = datetime.now()
            self.failure_count = 0
            self.healthy = True
        else:
            self.failure_count += 1
            if self.failure_count >= 3:
                self.healthy = False

        await self.save()

        latency_record = ModelLatency(
            model_source_id=self.id,
            latency=latency_ms,
            success=success,
            error_message=error_msg,
        )
        await latency_record.save()

        return self


class ModelLatency(BaseModel, TimestampMixin):
    """模型延迟检测历史"""

    id = fields.UUIDField(primary_key=True)
    model_source = fields.ForeignKeyField("app_system.ModelSource", related_name="latencies", on_delete=fields.CASCADE)
    latency = fields.FloatField(description="单次延迟值，单位秒")
    success = fields.BooleanField(description="此次检测是否成功")
    error_message = fields.TextField(null=True, description="检测失败时的错误信息")
    checked_time = fields.DatetimeField(auto_now_add=True, description="检测时间")

    class Meta:
        table = "model_latency"
