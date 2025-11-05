from typing import Optional

from pydantic import BaseModel, Field


class SensitiveWordBase(BaseModel):
    word: str = Field(..., alias="word")
    category_id: Optional[int] = Field(None, alias="categoryId")
    level: Optional[int] = Field(1, alias="level", ge=1, le=3)  # 限制级别在1-3之间
    description: Optional[str] = Field(None, alias="description")
    is_active: Optional[bool] = Field(True, alias="isActive")


class SensitiveWordCreate(SensitiveWordBase):
    pass


class SensitiveWordUpdate(SensitiveWordBase):
    word: Optional[str] = Field(None, alias="word")  # 更新时，敏感词可选


class SensitiveWordCategoryBase(BaseModel):
    name: str = Field(..., alias="name")
    description: Optional[str] = Field(None, alias="description")


class SensitiveWordCategoryCreate(SensitiveWordCategoryBase):
    pass


class SensitiveWordCategoryUpdate(SensitiveWordCategoryBase):
    name: Optional[str] = Field(None, alias="name")
