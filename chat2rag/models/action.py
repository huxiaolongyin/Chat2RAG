from tortoise import fields

from .base import BaseModel, TimestampMixin


class RobotAction(BaseModel, TimestampMixin):
    """机器人动作定义表 - 表示机器人可以执行的动作"""

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=50, unique=True, description="动作名称")
    code = fields.CharField(
        max_length=50, unique=True, db_index=True, description="动作代码"
    )
    description = fields.CharField(max_length=255, null=True, description="动作描述")
    is_active = fields.BooleanField(default=True, db_index=True, description="是否启用")

    class Meta:
        table = "robot_actions"
        indexes = ["is_active"]
