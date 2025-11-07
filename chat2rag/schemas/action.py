from typing import Optional

from pydantic import BaseModel, Field


class RobotActionBase(BaseModel):
    name: str = Field(..., max_length=50, description="动作名称")
    code: str = Field(..., max_length=50, description="动作代码")
    description: Optional[str] = Field(None, max_length=255, description="动作描述")
    is_active: bool = Field(True, description="是否启用", alias="isActive")


class RobotActionCreate(RobotActionBase):
    pass


class RobotActionUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50, description="动作名称")
    code: Optional[str] = Field(None, max_length=50, description="动作代码")
    description: Optional[str] = Field(None, max_length=255, description="动作描述")
    is_active: Optional[bool] = Field(None, description="是否启用", alias="isActive")
