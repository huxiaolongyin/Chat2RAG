from typing import Optional

from pydantic import BaseModel, Field


# ModelProvider (渠道商)
class ModelProviderBase(BaseModel):
    name: str = Field(..., max_length=100, description="渠道商名称，如OpenAI、Azure")
    base_url: Optional[str] = Field(None, description="渠道商API基础地址")
    api_key: Optional[str] = Field(None, description="调用API密钥")
    enabled: Optional[bool] = Field(True, description="是否启用")
    description: Optional[str] = Field(None, max_length=255, description="描述信息")


class ModelProviderCreate(ModelProviderBase):
    pass


class ModelProviderUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="渠道商名称")
    base_url: Optional[str] = Field(None, description="渠道商API基础地址")
    api_key: Optional[str] = Field(None, description="调用API密钥")
    enabled: Optional[bool] = Field(None, description="是否启用")
    description: Optional[str] = Field(None, max_length=255, description="描述信息")


# ModelSource (模型源)
class ModelSourceBase(BaseModel):
    alias: Optional[str] = Field(None, max_length=100, description="模型别名")
    enabled: Optional[bool] = Field(False, description="是否启用")
    priority: Optional[int] = Field(0, description="优先级，数值越大优先级越高")
    generation_kwargs: Optional[dict] = Field(
        {}, description="模型参数", alias="generationKwargs"
    )


class ModelSourceCreate(ModelSourceBase):
    provider_id: int = Field(..., description="所属渠道商ID", alias="provideId")
    name: str = Field(..., max_length=100, description="模型正式名称，如gpt-4")


class ModelSourceUpdate(ModelSourceBase): ...
