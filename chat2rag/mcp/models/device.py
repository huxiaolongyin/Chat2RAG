from tortoise import fields

from .base import BaseModel, TimestampMixin


class Device(BaseModel, TimestampMixin):
    """
    设备模型
    """

    id = fields.IntField(primary_key=True)
    vin = fields.CharField(max_length=100, description="设备名称")
    scene = fields.ForeignKeyField(model_name="app_system.Scene", description="场景")

    class Meta:
        table = "device"
