from datetime import datetime
from typing import List, Optional, TypeVar

from pydantic import Field, computed_field, field_validator

from .base import BaseSchema, PaginatedData

# 泛型类型变量，用于响应数据的类型提示
T = TypeVar("T")

# fmt: off
class PromptBase(BaseSchema):
    prompt_name: str = Field(..., examples=["测试的提示词"], pattern=r"^[a-zA-Z0-9\u4e00-\u9fa5_-]+$", max_length=50)
    prompt_desc: str = Field(..., examples=["测试提示词描述"], pattern=r"^[a-zA-Z0-9\u4e00-\u9fa5_-]+$", max_length=200)
    prompt_text: str = Field(..., examples=["这是测试提示词内容"])


class PromptCreate(PromptBase):

    @field_validator("prompt_name", "prompt_desc", "prompt_text")
    @classmethod
    def not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("不能为空")
        return v


class PromptUpdate(PromptBase):
    prompt_name: Optional[str] = Field(None, examples=["测试的提示词"])
    prompt_desc: Optional[str] = Field(None, examples=["测试提示词描述"])
    prompt_text: Optional[str] = Field(None, examples=["这是测试提示词内容"])


class PromptIdResponse(BaseSchema):
    prompt_id: int = Field(..., examples=[1])


class PromptItemResponse(BaseSchema):
    """单个提示词响应模型"""
    id: int = Field(..., examples=[1])
    prompt_name: str = Field(..., examples=["代码审查助手"])
    current_version: int = Field(..., examples=[3])
    prompt_text: str = Field(..., examples=["请仔细审查以下代码，重点关注代码质量、性能优化和潜在bug..."])
    prompt_desc: str = Field(..., examples=["用于代码审查的AI助手提示词，帮助识别代码问题并提供改进建议"])
    version: int = Field(..., examples=[3])
    create_time: datetime
    update_time: datetime
    

class PromptPaginatedData(BaseSchema):
    """提示词分页数据 - 兼容promptList字段格式"""
    
    prompt_list: List[PromptItemResponse] = Field(default_factory=list, description="提示词列表")
    total: int = Field(default=0, ge=0, description="总记录数")
    current: int = Field(default=1, ge=1, description="当前页码")
    size: int = Field(default=20, ge=1, description="每页条数")
    
    @computed_field
    @property
    def pages(self) -> int:
        """总页数"""
        return (self.total + self.size - 1) // self.size if self.total > 0 else 0
    
    @classmethod
    def create(
        cls,
        items: List[PromptItemResponse],
        total: int,
        current: int = 1,
        size: int = 20
    ) -> "PromptPaginatedData":
        """创建提示词分页数据"""
        return cls(
            prompt_list=items,
            total=total,
            current=current,
            size=size
        )
# fmt: on
