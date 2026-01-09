# chat2rag/mcp/models/cart.py
from tortoise import fields

from .base import BaseModel, TimestampMixin


class Cart(BaseModel, TimestampMixin):
    """
    购物车模型，绑定用户（user_id）
    """

    id = fields.IntField(primary_key=True)
    user_id = fields.CharField(max_length=100, description="用户唯一标识")
    # 用于关联，方便查明细
    # 可根据需要设唯一索引 user_id，保证每个用户只有一个购物车
    # 也可以支持多购物车，如订单购物车等，灵活调整

    class Meta:
        table = "cart"


class CartItem(BaseModel, TimestampMixin):
    """
    购物车菜品明细，绑定购物车和菜品，记录数量
    """

    id = fields.IntField(primary_key=True)
    cart = fields.ForeignKeyField("app_system.Cart", related_name="items", description="购物车")
    item = fields.ForeignKeyField("app_system.Item", description="关联菜品")
    quantity = fields.IntField(description="数量", default=1)

    class Meta:
        table = "cart_item"
        unique_together = ("cart", "item")
