# chat2rag/mcp/models/item.py
from tortoise import fields

from .base import BaseModel, TimestampMixin


class Item(BaseModel, TimestampMixin):
    """
    菜品模型
    """

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100, description="菜品名称")
    price = fields.DecimalField(max_digits=10, decimal_places=2, description="价格")
    image_url = fields.CharField(max_length=255, null=True, description="菜品图片URL")
    description = fields.TextField(null=True, description="菜品描述")

    class Meta:
        table = "item"
