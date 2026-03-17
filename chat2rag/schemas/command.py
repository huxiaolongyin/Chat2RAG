from enum import Enum
from typing import Any

from pydantic import Field

from .base import BaseSchema, IDMixin, TimestampMixin


class ParamType(str, Enum):
    """参数类型枚举"""

    NONE = "none"
    NUMBER = "number"
    TEXT = "text"


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


# CommandVariant Schemas
class CommandVariantBase(BaseSchema):
    text: str = Field(..., max_length=255, description="指令文本", examples=["音量调整到{num}"])
    pattern: str | None = Field(None, max_length=255, description="参数匹配模式", examples=["音量调整到{num}"])


class CommandVariantData(CommandVariantBase, IDMixin): ...


class CommandVariantCreate(CommandVariantBase): ...


# Command Schemas
class CommandBase(BaseSchema):
    name: str = Field(..., max_length=50, description="指令名称", examples=["向左转"])
    code: str = Field(..., max_length=50, description="指令代码", examples=["TurnLeft"])
    reply: str | None = Field(None, description="回复内容", examples=["好的"])
    category_id: int | None = Field(None, description="分类ID")
    priority: int = Field(0, description="优先级，数字越大优先级越高")
    description: str | None = Field(None, max_length=255, description="描述信息", examples=["左转"])
    is_active: bool = Field(True, description="是否启用")
    commands: str | None = Field(
        None,
        max_length=255,
        description="指令文本",
        examples=["再左转一下|向左|向左边转"],
    )
    param_type: ParamType = Field(ParamType.NONE, description="参数类型")
    examples: list[str] | None = Field(None, description="示例说法列表，用于LLM few-shot识别")


class CommandData(CommandBase, IDMixin, TimestampMixin):
    variants: list[CommandVariantData] = Field(default_factory=list, description="指令变体列表")


class CommandCreate(CommandBase):
    variants: list[CommandVariantCreate] | None = Field(None, description="指令变体列表")


class CommandUpdate(BaseSchema):
    name: str | None = Field(None, max_length=50, description="指令名称", examples=["向左转"])
    code: str | None = Field(None, max_length=50, description="指令代码", examples=["TurnLeft"])
    reply: str | None = Field(None, description="回复内容")
    category_id: int | None = Field(None, description="分类ID")
    priority: int | None = Field(None, description="优先级")
    description: str | None = Field(None, max_length=255, description="描述信息")
    is_active: bool | None = Field(None, description="是否启用")
    commands: str | None = Field(None, max_length=255, description="指令文本")
    param_type: ParamType | None = Field(None, description="参数类型")
    examples: list[str] | None = Field(None, description="示例说法列表")
    variants: list[CommandVariantCreate] | None = Field(None, description="指令变体列表")


class CommandMatchResult(BaseSchema):
    """命令匹配结果"""

    command: CommandData = Field(..., description="匹配的命令")
    param: dict[str, Any] = Field(default_factory=dict, description="提取的参数")


class CommandBatchMove(BaseSchema):
    """批量移动命令"""

    command_ids: list[int] = Field(..., description="命令ID列表")
    category_id: int | None = Field(None, description="目标分类ID，null表示移动到未分类")
