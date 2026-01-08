from pydantic import Field

from .base import BaseSchema, IDMixin, TimestampMixin


# CommandCategory Schemas
class CommandCategoryBase(BaseSchema):
    name: str = Field(..., max_length=50, description="分类名称", examples=["测试"])
    description: str | None = Field(None, max_length=255, description="描述信息", examples=["测试描述"])


class CommandCategoryData(CommandCategoryBase, IDMixin): ...


class CommandCategoryIdData(BaseSchema):
    category_id: int = Field(..., description="命令分类ID", examples=[1])


class CommandCategoryCreate(CommandCategoryBase):
    pass


class CommandCategoryUpdate(BaseSchema):
    name: str | None = Field(None, max_length=50, description="分类名称", examples=["测试"])
    description: str | None = Field(None, max_length=255, description="描述信息", examples=["测试描述"])


# Command Schemas
class CommandBase(BaseSchema):
    name: str = Field(..., max_length=50, description="指令名称", examples=["向左转"])
    code: str = Field(..., max_length=50, description="指令代码", examples=["TurnLeft"])
    reply: str | None = Field(None, description="回复内容", examples=["好的"])
    category_id: int | None = Field(None, description="分类ID")
    priority: int = Field(0, description="优先级，数字越大优先级越高")
    description: str | None = Field(None, max_length=255, description="描述信息", examples=["左转"])
    is_active: bool = Field(True, description="是否启用")
    commands: str | None = Field(None, max_length=255, description="指令文本", examples=["再左转一下|向左|向左边转"])


class CommandData(CommandBase, IDMixin, TimestampMixin): ...


class CommandCreate(CommandBase): ...


class CommandUpdate(CommandBase):
    name: str | None = Field(None, max_length=50, description="指令名称", examples=["向左转"])
    code: str | None = Field(None, max_length=50, description="指令代码", examples=["TurnLeft"])
    priority: int | None = Field(None, description="优先级")
    is_active: bool | None = Field(None, description="是否启用")
