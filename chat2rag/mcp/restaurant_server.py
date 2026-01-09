from dataclasses import asdict, dataclass
from typing import Annotated, Any, Dict, Optional

from fastapi.responses import JSONResponse
from init_data import execute_init_sql_once, modify_db
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from tortoise.expressions import Q

from chat2rag.mcp.config import SETTINGS
from chat2rag.mcp.logger import get_logger
from chat2rag.mcp.models.cart import Cart, CartItem
from chat2rag.mcp.models.item import Item
from chat2rag.mcp.utils import with_db

logger = get_logger("HTW_MCPServer-Restaurant")


@dataclass
class MCPResponse:
    code: str = "0000"
    msg: str = "OK"
    status: str = ""
    data: Dict[Any, Any] = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}

    def dict(self) -> dict:
        return asdict(self)


# 创建点餐MCP服务
mcp = FastMCP("MCP-SERVER-RESTAURANT", host="0.0.0.0", port=8334)


# 用户ID，模拟机器人vin或者用户唯一标识
Vin = Annotated[
    str, Field(description="机器人唯一识别vin码，用于确定要控制的特定机器人")
]
# UserId = Annotated[str, Field(description="设备的唯一标识，区分不同用户购物车")]

# 菜品id，数量
ItemId = Annotated[int, Field(description="菜品唯一ID")]
Quantity = Annotated[int, Field(description="数量，默认为1")]


@mcp.tool()
@with_db
async def show_item() -> Dict[str, Any]:
    "展示餐厅里的所有菜品，一般常用于加入购物车前获取item_id的过程"
    try:
        item_objs = await Item.all()
        data = [{"id": item.id, "name": item.name} for item in item_objs]
        return MCPResponse(msg="菜品列表", data=data)
    except Exception as e:
        logger.error(f"show_item error: {e}")
        return MCPResponse(code="4003", msg="获取菜品失败").dict()


@mcp.tool()
@with_db
async def add_to_cart(
    user_id: Vin, item_id: ItemId, quantity: Quantity = 1
) -> Dict[str, Any]:
    """当用户想要进行点餐、加购时，选择某个菜品，则向购物车添加菜品，如果购物车无该菜品则新增，有则增加数量。例如：我想要点***菜"""
    try:
        item = await Item.get_or_none(id=item_id)
        if not item:
            return MCPResponse(code="4002", msg="菜品不存在").dict()

        cart, _ = await Cart.get_or_create(user_id=user_id)
        cart_item, created = await CartItem.get_or_create(cart=cart, item=item)
        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity
        await cart_item.save()
        return MCPResponse(msg=f"已添加 {quantity} 份 {item.name} 到购物车").dict()
    except Exception as e:
        logger.error(f"add_to_cart error: {e}")
        return MCPResponse(code="4003", msg="添加购物车失败").dict()


@mcp.tool()
@with_db
async def remove_from_cart(
    user_id: Vin, item_id: ItemId, quantity: Quantity = 1
) -> Dict[str, Any]:
    """当用户想要删除、或者不要购物车中某个菜品时使用。例如：我不想要刚刚的***了"""
    try:
        cart = await Cart.get_or_none(user_id=user_id)
        if not cart:
            return MCPResponse(code="4004", msg="购物车不存在").dict()

        cart_item = await CartItem.get_or_none(cart=cart, item_id=item_id)
        if not cart_item:
            return MCPResponse(code="4005", msg="购物车中无此菜品").dict()

        if cart_item.quantity <= quantity:
            await cart_item.delete()
            msg = f"已从购物车移除菜品"
        else:
            cart_item.quantity -= quantity
            await cart_item.save()
            msg = f"已减少 {quantity} 份该菜品数量"

        return MCPResponse(msg=msg).dict()
    except Exception as e:
        logger.error(f"remove_from_cart error: {e}")
        return MCPResponse(code="4006", msg="删除购物车菜品失败").dict()


@mcp.tool()
@with_db
async def view_cart(user_id: Vin) -> Dict[str, Any]:
    """当用户确认结束点餐过程时，展示所有点餐内容及价格。例如：好了，暂时就这些菜"""
    try:
        cart = await Cart.get_or_none(user_id=user_id)
        if not cart:
            return MCPResponse(
                msg="购物车为空", data={"items": [], "total_price": 0.0}
            ).dict()

        cart_items = await CartItem.filter(cart=cart).prefetch_related("item")
        items_list = []
        total_price = 0.0
        for ci in cart_items:
            sub_total = ci.quantity * float(ci.item.price)
            total_price += sub_total
            items_list.append(
                {
                    "item_id": ci.item.id,
                    "name": ci.item.name,
                    "quantity": ci.quantity,
                    "unit_price": float(ci.item.price),
                    "sub_total": sub_total,
                }
            )

        return MCPResponse(
            msg="购物车内容",
            data={"items": items_list, "total_price": round(total_price, 2)},
        ).dict()
    except Exception as e:
        logger.error(f"view_cart error: {e}")
        return MCPResponse(code="4007", msg="查看购物车失败").dict()


@mcp.tool()
@with_db
async def confirm_order(user_id: Vin) -> Dict[str, Any]:
    """用户确认购物车中所点的菜品时，进行订单确认及发起支付流程。例如: 确认就这些菜"""
    try:
        cart = await Cart.get_or_none(user_id=user_id)
        if not cart:
            return MCPResponse(code="4008", msg="购物车为空，无法确认订单").dict()

        cart_items_count = await CartItem.filter(cart=cart).count()
        if cart_items_count == 0:
            return MCPResponse(code="4008", msg="购物车为空，无法确认订单").dict()

        # 这里只演示逻辑，业务可以加入订单数据保存等
        return MCPResponse(
            msg="订单已确认，请进行支付", data={"order_status": "confirmed"}
        ).dict()
    except Exception as e:
        logger.error(f"confirm_order error: {e}")
        return MCPResponse(code="4009", msg="确认订单失败").dict()


# @mcp.tool()
# @with_db
# async def pay_order(user_id: Vin, payment_info: str) -> Dict[str, Any]:
#     """模拟支付流程"""
#     try:
#         # 这里仅示范，实际业务中要校验订单状态和支付信息
#         logger.info(f"用户 {user_id} 支付信息: {payment_info}")
#         # 标记订单已支付
#         return MCPResponse(msg="支付成功，订单完成").dict()
#     except Exception as e:
#         logger.error(f"pay_order error: {e}")
#         return MCPResponse(code="4010", msg="支付失败").dict()


if __name__ == "__main__":
    import asyncio

    async def main():
        await modify_db(SETTINGS.TORTOISE_ORM)

    asyncio.run(main())
    # print(asyncio.run(show_item()))

    mcp.run(transport="streamable-http")
