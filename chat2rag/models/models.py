from tortoise import fields

from .base import BaseModel, TimestampMixin


class ModelProvider(BaseModel, TimestampMixin):
    id = fields.IntField(pk=True)
    name = fields.CharField(
        max_length=100,
        unique=True,
        description="渠道商名称，如OpenAI、Azure、Anthropic",
    )
    base_url = fields.TextField(null=True, description="渠道商默认API地址")
    api_key = fields.TextField(description="调用API密钥或令牌")
    enabled = fields.BooleanField(default=True, description="渠道商是否启用")
    description = fields.TextField(null=True, description="渠道商描述")

    class Meta:
        table = "model_providers"


class ModelSource(BaseModel, TimestampMixin):
    id = fields.IntField(pk=True)
    provider = fields.ForeignKeyField(
        "app_system.ModelProvider",
        related_name="sources",
        on_delete=fields.CASCADE,
        description="所属渠道商",
    )
    name = fields.CharField(max_length=100)
    alias = fields.CharField(max_length=100, null=True)
    enabled = fields.BooleanField(default=False)
    last_latency = fields.FloatField(null=True, description="最近一次检测的延迟，秒")
    last_check_time = fields.DatetimeField(
        null=True, description="最近一次延迟检测时间"
    )
    healthy = fields.BooleanField(default=False, description="是否健康可用")
    failure_count = fields.IntField(default=0, description="连续调用失败次数")
    priority = fields.IntField(default=0, description="优先级，数值越大优先级越高")
    generation_kwargs = fields.JSONField(null=True)

    class Meta:
        table = "model_sources"


class ModelLatency(BaseModel, TimestampMixin):
    """模型延迟检测历史"""

    id = fields.UUIDField(pk=True)
    model_source = fields.ForeignKeyField(
        "app_system.ModelSource", related_name="latencies", on_delete=fields.CASCADE
    )
    latency = fields.FloatField(description="单次延迟值，单位秒")
    success = fields.BooleanField(description="此次检测是否成功")
    error_message = fields.TextField(null=True, description="检测失败时的错误信息")
    checked_time = fields.DatetimeField(auto_now_add=True, description="检测时间")

    class Meta:
        table = "model_latency"
