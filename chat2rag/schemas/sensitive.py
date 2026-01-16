from pydantic import Field

from .base import BaseSchema, IDMixin


class SensitiveWordBase(BaseSchema):
    word: str = Field(...)
    category_id: int | None = Field(None)
    level: int | None = Field(1, ge=1, le=3)  # 限制级别在1-3之间
    description: str | None = Field(None)
    is_active: bool | None = Field(True)


class SensitiveWordData(IDMixin, SensitiveWordBase): ...


class SensitiveWordCreate(SensitiveWordBase): ...


class SensitiveWordUpdate(SensitiveWordBase):
    word: str | None = Field(None)  # 更新时，敏感词可选


class SensitiveWordCategoryBase(BaseSchema):
    name: str = Field(...)
    description: str | None = Field(None)


class SensitiveWordCategoryData(IDMixin, SensitiveWordCategoryBase): ...


class SensitiveWordCategoryCreate(SensitiveWordCategoryBase): ...


class SensitiveWordCategoryUpdate(SensitiveWordCategoryBase):
    name: str | None = Field(None)
