from .base import BaseModel, TimestampMixin
from tortoise import fields


class Scene(BaseModel, TimestampMixin):
    """
    场景模型
    """

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100, description="场景名称")
    description = fields.TextField(description="场景描述", null=True)

    class Meta:
        table = "scene"
