from dataclasses import asdict, dataclass
from enum import Enum
from typing import Annotated, Any, Dict, Optional, Union

from cachetools import TTLCache
from fastapi.responses import JSONResponse
from init_data import execute_init_sql_once, modify_db
from mcp.server.fastmcp import FastMCP
from openai import AsyncOpenAI
from pydantic import Field
from tortoise.expressions import Q

from chat2rag.mcp.config import SETTINGS
from chat2rag.mcp.logger import get_logger
from chat2rag.mcp.models.cart import Cart, CartItem
from chat2rag.mcp.models.device import Device
from chat2rag.mcp.models.entity import Entity
from chat2rag.mcp.models.item import Item
from chat2rag.mcp.utils import with_db

logger = get_logger("HTW_MCPServer")

state: Dict[str, Dict[str, Any]] = TTLCache(maxsize=100, ttl=300)

client = AsyncOpenAI(
    api_key="sk-xanhyopslamqkebregfhldoudjkjyunlhebkrcslwlbbsuyu",
    base_url="https://api.siliconflow.cn/v1",
)


@dataclass
class HTWResponse:
    code: str = "0000"
    msg: str = "OK"
    status: str = ""
    data: Dict[Any, Any] = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}

    def dict(self) -> dict:
        return asdict(self)


class NavigationStatus:
    ENTITY_NOT_FOUND = "entity_not_found"  # 未找到匹配地点
    UNABLE_TO_GUIDE = "unable_to_guide"  # 无法带路
    AWAITING_CONFIRM = "awaiting_confirm"  # 等待用户二次确认
    GUIDING = "guiding"  # 正在导航中


# Create an MCP server
mcp = FastMCP("MCP-SERVER-HTW", host="0.0.0.0", port=8333)


Vin = Annotated[str, Field(description="机器人唯一识别vin码，用于确定要控制的特定机器人")]
Destination = Annotated[
    str, Field(description="导航目标地点实体名称，使用简洁的名词，无需添加形容词或地点修饰词，例如'会议室'、'前台'等")
]
NavigationConfirm = Annotated[
    bool, Field(description="导航二次确认，得到用户二次确认后启动导航服务，默认为False，得到确认后为True")
]
EntityId = Annotated[Union[int, str], Field(description="目标地点的唯一ID，用于确认导航")]

ItemName = Annotated[str, Field(description="菜品的名称")]
Quantity = Annotated[int, Field(description="增加或减少的数量，默认为1，减少时使用负数")]
IsPAY = Annotated[int, Field(description="是否进入支付环节，0代表展示购物车列表，1代表进入支付阶段，默认0")]


# Add an addition tool
@mcp.tool()
@with_db
async def navigate_to_location(
    vin: Vin,
    destination: Destination,
    navigation_confirm: NavigationConfirm = False,
    entity_id: EntityId = "",
):
    # -> Dict[str, Union[bool, str, Dict]]
    """使用机器人进行室内及周边的实体点位路线指引或带路，无法判断哪个点位最近"""
    try:
        # 查找机器人
        device = await Device.filter(vin=vin).prefetch_related("scene").first()
        if not device:
            msg = f"未找到机器人: {vin}"
            logger.warning(msg)
            return HTWResponse(code="4000", status=NavigationStatus.ENTITY_NOT_FOUND, msg=msg).dict()

        # 查找场景
        scene = device.scene
        if not scene:
            msg = "未找到场景或机器人未绑定场景"
            logger.warning(msg)
            return HTWResponse(code="4000", status=NavigationStatus.ENTITY_NOT_FOUND, msg=msg).dict()

        # 查找实体
        exact_match_query = Q(Q(name=destination) | Q(common_name=destination) | Q(alias__contains=destination)) & Q(
            scenes=scene
        )
        entities = await Entity.filter(exact_match_query)

        #
        if not entities:
            msg = f"在场景:{scene.name} 下未找到{destination}"
            logger.warning(msg)
            return HTWResponse(code="4000", status=NavigationStatus.ENTITY_NOT_FOUND, msg=msg).dict()

        common_name = entities[0].common_name  # 通用名
        is_reachable = entities[0].is_reachable  # 可到达性

        # 找到所有通用名一致的实体
        if common_name:
            similar_entities = [{"name": e.name, "entity_id": e.id} for e in entities if e.common_name == common_name]
        else:
            similar_entities = [{"name": e.name, "entity_id": e.id} for e in entities]

        if not navigation_confirm:
            data = {
                "common_name": common_name,
                "entities": similar_entities,
                "is_reachable": is_reachable,
            }
            logger.info(f"检索实体数据: {data}")
            if not is_reachable:
                msg = f"找到了'{destination}'，但该地点不可到达，无法带路，可以展示路线图：https://www.vgosaas.com/img/index/6-2.jpg"
                logger.info(msg)
                return HTWResponse(msg=msg, status=NavigationStatus.UNABLE_TO_GUIDE, data=data).dict()

            msg = f"找到了'{destination}'，是否需要我带路前往？请确认。"

            return HTWResponse(
                msg=msg,
                status=NavigationStatus.AWAITING_CONFIRM,
                data=data,
            ).dict()

        # 步骤2: 确认导航
        if not entity_id:
            msg = "启动导航需要提供entity_id，请提供entity_id"
            logger.warning(msg)
            return HTWResponse(status=NavigationStatus.ENTITY_NOT_FOUND, msg=msg).dict()

        if int(entity_id) not in [entity.id for entity in entities]:
            msg = f"传入entity_id与给定实体名称{destination}不一致"
            logger.warning(msg)
            return HTWResponse(status=NavigationStatus.ENTITY_NOT_FOUND, msg=msg).dict()

        entity = await Entity.get_or_none(id=entity_id)
        msg = f"设备{vin}确认进行地点: {entity.name}的路线导航"
        data = {
            "vin": vin,
            "entity_id": entity_id,
            "entity": entity.name,
        }
        return HTWResponse(msg=msg, data=data, status=NavigationStatus.GUIDING).dict()
    except Exception as e:
        msg = f"lead_way错误: {str(e)}"
        logger.error(msg)
        return HTWResponse(status=NavigationStatus.ENTITY_NOT_FOUND, msg=msg).dict()


@with_db
async def get_item_id(item_name: str) -> Item:
    """使用大模型判断是否是菜单中菜品，是则返回id，否为空"""
    items = await Item.all()
    item_names = [{"id": item.id, "name": item.name} for item in items]
    system_prompt = """
    你是菜品ID检索工具，用于处理用户在说简写时，判断菜品的唯一ID，保证流程处理的准确性，最后返回ID。
    要求: 仅返回ID，无需其他的任何内容，如果没有检索到，则返回 None
    例如，用户说 鸭汤，则返回滋补老鸭汤的ID:1
    """
    prompt = f"用户说的菜品名称：{item_name}，判断是否是所有菜品{item_names}的其中之一，请返回ID"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    response = await client.chat.completions.create(
        model="Qwen/Qwen2.5-32B-Instruct",
        messages=messages,
        max_tokens=10,
        temperature=0,
    )

    answer = response.choices[0].message.content.strip()
    if answer and answer.isdigit():
        return await Item.get_or_none(id=int(answer))
    return None


@mcp.tool()
async def cart_manage(user_id: Vin, item_name: ItemName, quantity: Quantity = 1) -> Dict[str, Any]:
    """汉特云餐厅的点餐流程，当用户想要进行点餐、加购时或去除某个菜时使用。选择某个菜品，则向购物车添加菜品，如果购物车无该菜品则新增，有则增加数量。例如：我想要点某个菜，或我想去掉某个菜"""
    try:
        item = await get_item_id(item_name)
        if not item:
            return HTWResponse(
                code="4002",
                msg="菜品不存在，请查看菜单: [IMAGE:https://pic.nximg.cn/file/20230620/27674834_161855683102_2.jpg]",
            ).dict()

        cart = state.get(user_id, {})

        # 如果quantity为负数且购物车无该商品，直接返回提示
        if quantity < 0 and not cart:
            return HTWResponse(code="4004", msg=f"购物车中无{item_name}，无法减少数量").dict()

        if cart.get(item):
            cart[item] += quantity
            if cart[item] <= 0:
                cart.pop(item)
                state[user_id] = cart
                return HTWResponse(msg=f"{item_name} 已从购物车移除").dict()
        else:
            if quantity <= 0:
                return HTWResponse(code="4005", msg="添加的数量必须大于0").dict()

            cart[item] = quantity
            state[user_id] = cart

        return HTWResponse(
            msg=f"已更新购物车: {quantity} 份 {item_name}，可以查看菜单: [IMAGE:https://pic.nximg.cn/file/20230620/27674834_161855683102_2.jpg]，继续点餐，也可直接说结算"
        ).dict()

    except Exception as e:
        logger.error(f"cart_manage error: {e}")
        return HTWResponse(code="4003", msg="操作购物车失败").dict()


@mcp.tool()
@with_db
async def checkout(user_id: Vin, confirmed: bool = False) -> Dict[str, Any]:
    """
    汉特云餐厅的结算流程（必须按步骤执行）。

    【重要】流程说明：
    1. 第一步(confirmed=False)：展示购物车菜品及总价，让用户确认
    2. 第二步(confirmed=True)：用户明确确认后，生成支付二维码

    【使用规则】
    - 用户说"结算/买单/就这些了" → 调用 checkout(confirmed=False)
    - 用户说"确认/没问题/OK/对的" → 调用 checkout(confirmed=True)
    - 禁止跳过确认步骤直接生成二维码！

    示例对话：
        用户：结算吧
        → checkout(user_id, confirmed=False) → 返回购物车内容
        用户：没问题
        → checkout(user_id, confirmed=True) → 返回支付二维码
    """
    try:
        cart = state.get(user_id, {})

        # 购物车为空检查
        if not cart:
            return HTWResponse(
                code="4006",
                msg="购物车为空，请先点餐。可查看菜单: [IMAGE:https://pic.nximg.cn/file/20230620/27674834_161855683102_2.jpg]",
                data={"items": [], "total_price": 0.0},
            ).dict()

        # 计算购物车内容
        items_list = []
        total_price = 0.0
        for key, value in cart.items():
            unit_price = float(key.price)
            sub_total = value * unit_price
            total_price += sub_total
            items_list.append(
                {
                    "item_id": key.id,
                    "name": key.name,
                    "quantity": value,
                    "unit_price": unit_price,
                    "sub_total": round(sub_total, 2),
                }
            )
        total_price = round(total_price, 2)

        # 第一步：展示购物车，等待确认
        if not confirmed:
            return HTWResponse(
                msg="请确认您的订单内容，确认无误后请回复'确认'或'没问题'",
                data={
                    "items": items_list,
                    "total_price": total_price,
                    "status": "pending_confirmation",  # 标记状态
                },
            ).dict()

        # 第二步：用户已确认，生成支付二维码
        payment_qr_url = "[IMAGE:https://pic.baike.soso.com/p/20130307/20130307133541-2131676630.jpg]"

        # 清空购物车
        state.pop(user_id, None)

        return HTWResponse(
            msg="订单已确认，请扫码支付",
            data={
                "items": items_list,
                "total_price": total_price,
                "payment_qr": payment_qr_url,
                "status": "payment_ready",
            },
        ).dict()

    except Exception as e:
        logger.error(f"checkout error: {e}")
        return HTWResponse(code="4007", msg="结算流程出错").dict()


if __name__ == "__main__":
    # 数据库变更
    import asyncio

    # print(asyncio.run(get_item_id("虾滑")))

    async def main():
        await modify_db(SETTINGS.TORTOISE_ORM)
        await execute_init_sql_once()

    asyncio.run(main())

    mcp.run(transport="streamable-http")
