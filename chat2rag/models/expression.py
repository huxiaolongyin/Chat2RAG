from tortoise import fields

from .base import BaseModel, TimestampMixin


class RobotExpression(BaseModel, TimestampMixin):
    """机器人表情定义表 - 代表机器人可以做出的表情"""

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=50, unique=True, description="表情名称")
    code = fields.CharField(max_length=50, unique=True, db_index=True, description="表情代码")
    description = fields.CharField(max_length=255, null=True, description="表情描述")
    is_active = fields.BooleanField(default=True, db_index=True, description="是否启用")

    class Meta:
        table = "robot_expressions"
        indexes = ["is_active"]
