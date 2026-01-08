from pydantic import Field

from .base import BaseSchema, IDMixin, TimestampMixin


class RobotActionBase(BaseSchema):
    name: str = Field(..., max_length=50, description="动作名称", examples=["挥手"])
    code: str = Field(..., max_length=50, description="动作代码", examples=["WaveHands"])
    description: str | None = Field(None, max_length=255, description="动作描述", examples=["用于机器人上下摆动右手"])
    is_active: bool = Field(True, description="是否启用")


class RobotActionData(RobotActionBase, TimestampMixin, IDMixin): ...


class RobotActionCreate(RobotActionBase): ...


class RobotActionUpdate(BaseSchema):
    name: str | None = Field(None, max_length=50, description="动作名称", examples=["挥手"])
    code: str | None = Field(None, max_length=50, description="动作代码", examples=["WaveHands"])
    description: str | None = Field(None, max_length=255, description="动作描述", examples=["用于机器人上下摆动右手"])
    is_active: bool | None = Field(None, description="是否启用", alias="isActive")
