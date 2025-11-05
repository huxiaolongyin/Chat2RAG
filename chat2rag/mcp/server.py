from dataclasses import asdict, dataclass
from typing import Annotated, Any, Dict, Optional, Union

from fastapi.responses import JSONResponse
from init_data import execute_init_sql_once, modify_db
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from tortoise.expressions import Q

from chat2rag.mcp.config import SETTINGS
from chat2rag.mcp.logger import get_logger
from chat2rag.mcp.models.device import Device
from chat2rag.mcp.models.entity import Entity
from chat2rag.mcp.utils import with_db

logger = get_logger("HTW_MCPServer")


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


# fmt: off
Vin = Annotated[str, Field(description="机器人唯一识别vin码，用于确定要控制的特定机器人")]
Destination = Annotated[str, Field(description="导航目标地点实体名称，使用简洁的名词，无需添加形容词或地点修饰词，例如'会议室'、'前台'等")]
NavigationConfirm = Annotated[bool, Field(description="导航二次确认，得到用户二次确认后启动导航服务，默认为False，得到确认后为True")]
EntityId = Annotated[str, Field(description="目标地点的唯一ID，用于确认导航")]


# fmt: on
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
            return HTWResponse(
                code="4000", status=NavigationStatus.ENTITY_NOT_FOUND, msg=msg
            ).dict()

        # 查找场景
        scene = device.scene
        if not scene:
            msg = "未找到场景或机器人未绑定场景"
            logger.warning(msg)
            return HTWResponse(
                code="4000", status=NavigationStatus.ENTITY_NOT_FOUND, msg=msg
            ).dict()

        # 查找实体
        exact_match_query = Q(
            Q(name=destination)
            | Q(common_name=destination)
            | Q(alias__contains=destination)
        ) & Q(scenes=scene)
        entities = await Entity.filter(exact_match_query)

        #
        if not entities:
            msg = f"在场景:{scene.name} 下未找到{destination}"
            logger.warning(msg)
            return HTWResponse(
                code="4000", status=NavigationStatus.ENTITY_NOT_FOUND, msg=msg
            ).dict()

        common_name = entities[0].common_name  # 通用名
        is_reachable = entities[0].is_reachable  # 可到达性

        # 找到所有通用名一致的实体
        if common_name:
            similar_entities = [
                {"name": e.name, "entity_id": e.id}
                for e in entities
                if e.common_name == common_name
            ]
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
                return HTWResponse(
                    msg=msg, status=NavigationStatus.UNABLE_TO_GUIDE, data=data
                ).dict()

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


if __name__ == "__main__":
    # 数据库变更
    import asyncio

    async def main():
        await modify_db(SETTINGS.TORTOISE_ORM)
        await execute_init_sql_once()

    asyncio.run(main())

    # mcp.run(transport="streamable-http")
    mcp.run(transport="streamable-http")
