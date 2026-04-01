from datetime import datetime

from pydantic import Field

from chat2rag.core.enums import ModelCapability

from .base import BaseSchema, IDMixin, TimestampMixin


# ModelProvider (渠道商)
class ModelProviderBase(BaseSchema):
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="渠道商名称，如OpenAI、Azure",
        examples=["阿里"],
    )
    base_url: str = Field(
        ..., description="渠道商API基础地址", examples=["https://..."]
    )
    api_key: str = Field(..., description="调用API密钥", examples=["sk-..."])
    enabled: bool | None = Field(True, description="是否启用")
    description: str | None = Field(
        None, max_length=255, description="描述信息", examples=["阿里大模型"]
    )


class ModelProviderData(ModelProviderBase, IDMixin): ...


class ModelProviderIdData(BaseSchema):
    model_provider_id: int = Field(..., description="模型渠道商ID", examples=[1])


class ModelProviderCreate(ModelProviderBase): ...


class ModelProviderUpdate(BaseSchema):
    name: str | None = Field(
        None,
        max_length=100,
        description="渠道商名称，如OpenAI、Azure",
        examples=["阿里"],
    )
    base_url: str | None = Field(
        None, description="渠道商API基础地址", examples=["https://..."]
    )
    api_key: str | None = Field(None, description="调用API密钥", examples=["sk-..."])
    enabled: bool | None = Field(None, description="是否启用")
    description: str | None = Field(
        None, max_length=255, description="描述信息", examples=["阿里大模型"]
    )


# ModelSource (模型源)
class ModelSourceBase(BaseSchema):
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="模型正式名称，如gpt-4",
        examples=["gpt-4"],
    )
    alias: str | None = Field(
        None, max_length=100, description="模型别名", examples=["Qwen3-32B"]
    )
    enabled: bool | None = Field(None, description="是否启用")
    healthy: bool | None = Field(None, description="是否健康可用")
    priority: int | None = Field(None, description="优先级，数值越大优先级越高")
    generation_kwargs: dict | None = Field(None, description="模型参数")
    capabilities: list[ModelCapability] = Field(
        default=[ModelCapability.TEXT], description="支持的能力类型"
    )


class ModelSourceData(ModelSourceBase, IDMixin, TimestampMixin):
    failure_count: int = Field(0, description="连续调用失败次数")
    provider_id: int = Field(..., description="模型渠道商ID", examples=[1])
    last_latency: float | None = Field(None, description="最近一次检测的延迟，秒")
    last_check_time: datetime | None = Field(None, description="最近一次延迟检测时间")


class ModelSourceCreate(ModelSourceBase):
    provider_id: int = Field(..., description="所属渠道商ID")


class ModelSourceUpdate(ModelSourceBase):
    name: str | None = Field(
        None, max_length=100, description="模型正式名称，如gpt-4", examples=["gpt-4"]
    )
    capabilities: list[ModelCapability] | None = Field(
        None, description="支持的能力类型"
    )


class ModelSourceOption(BaseSchema):
    """模型源的选项"""

    name: str = Field(..., description="模型别名", examples=["Qwen3-32B"])
    id: str = Field(..., description="模型别名", examples=["Qwen3-32B"])
