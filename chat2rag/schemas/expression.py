from typing import Optional

from pydantic import Field

from .base import BaseSchema, IDMixin, TimestampMixin


class RobotExpressionBase(BaseSchema):
    name: str = Field(..., max_length=50, description="表情名称")
    code: str = Field(..., max_length=50, description="表情代码")
    description: Optional[str] = Field(None, max_length=255, description="表情描述")
    is_active: bool = Field(True, description="是否启用", alias="isActive")


class RobotExpressionData(RobotExpressionBase, TimestampMixin, IDMixin): ...


class RobotExpressionCreate(RobotExpressionBase): ...


class RobotExpressionUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=50, description="表情名称")
    code: Optional[str] = Field(None, max_length=50, description="表情代码")
    description: Optional[str] = Field(None, max_length=255, description="表情描述")
    is_active: Optional[bool] = Field(None, description="是否启用", alias="isActive")
