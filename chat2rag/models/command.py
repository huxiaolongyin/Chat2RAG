from tortoise import fields

from .base import BaseModel, TimestampMixin


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

    class Meta:
        table = "commands"
        indexes = [
            ("is_active", "priority"),  # 复合索引：查询启用指令并排序
            ("category", "is_active"),  # 按分类查询启用指令
        ]


class CommandVariant(BaseModel, TimestampMixin):
    """指令变体表 - 存储同一指令的不同说法"""

    id = fields.IntField(primary_key=True)
    command = fields.ForeignKeyField(
        "app_system.Command", related_name="variants", on_delete=fields.CASCADE
    )
    text = fields.CharField(max_length=255, db_index=True, description="指令文本")

    class Meta:
        table = "command_variants"
        indexes = [("command", "text")]
