from tortoise import fields
from .base import BaseModel, TimestampMixin


class Entity(BaseModel, TimestampMixin):
    """
    实体模型
    """

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100, description="实体名称")
    common_name = fields.CharField(max_length=100, description="通用名", null=True)
    alias = fields.CharField(max_length=255, description="别名", null=True)
    allow_nearest = fields.BooleanField(description="是否允许最近匹配")
    is_reachable = fields.BooleanField(description="是否可到达")
    scenes = fields.ManyToManyField("app_system.Scene", related_name="entities")

    class Meta:
        table = "entity"
