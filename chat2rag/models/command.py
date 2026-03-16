import enum

from tortoise import fields

from .base import BaseModel, TimestampMixin


class ParamType(str, enum.Enum):
    """参数类型枚举"""

    NONE = "none"
    NUMBER = "number"
    TEXT = "text"


class CommandCategory(BaseModel, TimestampMixin):
    """机器人指令分类表"""

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=50, unique=True, description="分类名称")
    description = fields.CharField(max_length=255, null=True, description="描述信息")

    class Meta:
        table = "command_categories"


class Command(BaseModel, TimestampMixin):
    """机器人固定指令表"""

    id = fields.IntField(primary_key=True)
    name = fields.CharField(
        max_length=50, unique=True, db_index=True, description="指令名称"
    )
    code = fields.CharField(
        max_length=50, unique=True, db_index=True, description="指令代码"
    )
    reply = fields.TextField(null=True, description="回复内容")
    category = fields.ForeignKeyField(
        "app_system.CommandCategory",
        related_name="commands",
        null=True,
        on_delete=fields.SET_NULL,
        description="分类ID",
    )
    priority = fields.IntField(default=0, description="优先级，数字越大优先级越高")
    description = fields.CharField(max_length=255, null=True, description="描述信息")
    is_active = fields.BooleanField(default=True, db_index=True, description="是否启用")
    param_type = fields.CharEnumField(
        ParamType, default=ParamType.NONE, description="参数类型"
    )
    examples = fields.JSONField(
        null=True, default=[], description="示例说法列表，用于LLM few-shot识别"
    )

    class Meta:
        table = "commands"
        indexes = [
            ("is_active", "priority"),
            ("category", "is_active"),
        ]


class CommandVariant(BaseModel, TimestampMixin):
    """指令变体表 - 存储同一指令的不同说法"""

    id = fields.IntField(primary_key=True)
    command = fields.ForeignKeyField(
        "app_system.Command", related_name="variants", on_delete=fields.CASCADE
    )
    text = fields.CharField(max_length=255, db_index=True, description="指令文本")
    pattern = fields.CharField(
        max_length=255, null=True, description="参数匹配模式，如：音量调整到{num}"
    )

    class Meta:
        table = "command_variants"
        indexes = [("command", "text")]
