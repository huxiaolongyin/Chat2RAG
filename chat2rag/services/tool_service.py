from typing import List, Optional

from tortoise.expressions import Q

from chat2rag.core.crud import CRUDBase
from chat2rag.core.tools.mcp import MCPConnectionManager
from chat2rag.logger import get_logger
from chat2rag.models import APITool, MCPServer, MCPTool
from chat2rag.schemas.tools import (
    APIToolCreate,
    APIToolUpdate,
    MCPServerCreate,
    MCPServerUpdate,
)

logger = get_logger(__name__)
connection_manager = MCPConnectionManager()


class APIToolService(CRUDBase[APITool, APIToolCreate, APIToolUpdate]):
    def __init__(self):
        super().__init__(APITool)


class MCPService(CRUDBase[MCPServer, MCPServerCreate, MCPServerUpdate]):
    def __init__(self):
        super().__init__(MCPServer)

    async def get_by_names(self, names: list):

        if not names:
            return []

        query = MCPTool.filter(name__in=names).prefetch_related("server")
        tools = await query.all()

        if not tools:
            return []

        # 去重获取所有相关的服务器
        mcp_servers: set[MCPServer] = {tool.server for tool in tools}

        # 收集所有工具
        all_mcp_tools = []

        # 为每个服务器创建 toolset 并收集工具
        for server in mcp_servers:
            try:
                # 根据不同类型创建 server_info
                toolset = await connection_manager.get_toolset(server)

                # 只添加名字匹配的工具
                matched_tools = [tool for tool in toolset.tools if tool.name in names]
                all_mcp_tools.extend(matched_tools)

            except Exception as e:
                # 记录错误但继续处理其他服务器
                logger.error(f"Error connecting to server {server}: {e}")
                continue

        return all_mcp_tools

    async def get_mcp_tool_list(
        self,
        page: int = 1,
        page_size: int = 10,
        search: Q = None,
        order: list = None,
    ):
        """获取MCP工具列表（展开所有MCP服务器的工具）"""
        query = MCPTool.all()

        if search:
            query = query.filter(search)

        # 预加载服务器信息
        query = query.prefetch_related("server")

        # 获取总数
        total = await query.count()

        # 排序
        if order:
            query = query.order_by(*order)

        # 分页
        offset = (page - 1) * page_size
        tools = await query.offset(offset).limit(page_size).all()

        return total, tools

    async def create(self, obj_in: MCPServerCreate, exclude=None):
        mcp_server = await super().create(obj_in, exclude)

        # 如果服务器启用，则获取并创建工具
        if mcp_server.is_active:
            await self._sync_tools(mcp_server)

        return mcp_server

    async def update(
        self, id: int, obj_in: MCPServerUpdate, exclude: Optional[List[str]] = None
    ) -> MCPServer:
        """更新MCP服务器，如果配置改变则重新同步工具"""
        old_server = await self.get(id)
        if not old_server:
            return None

        server = await super().update(id, obj_in, exclude)

        # 检查是否需要重新同步工具
        config_changed = any(
            [
                hasattr(obj_in, attr) and getattr(obj_in, attr) is not None
                for attr in ["url", "command", "args", "env", "mcp_type"]
            ]
        )

        if config_changed or (hasattr(obj_in, "is_active") and obj_in.is_active):
            await self._sync_tools(server)
        elif hasattr(obj_in, "is_active") and not obj_in.is_active:
            # 如果禁用服务器，也禁用所有工具
            await MCPTool.filter(server=server).update(is_active=False)

        return server

    async def remove(self, id: int) -> bool:
        """删除MCP服务器，级联删除所有关联工具"""
        server = await self.get(id)

        if not server:
            return False

        # 删除所有关联的工具
        await MCPTool.filter(server=server).delete()

        # 删除服务器
        return await super().remove(id)

    async def sync_tools(self, server_id: int) -> List[MCPTool]:
        """手动同步指定服务器的工具"""
        server = await self.get(server_id)
        if not server:
            return []

        return await self._sync_tools(server)

    async def _sync_tools(self, server: MCPServer) -> List[MCPTool]:
        """从MCP服务器获取工具列表并同步到数据库"""
        try:
            # 检查服务器是否启用且有URL
            if not server.is_active or not server.url:
                return []

            toolset = await connection_manager.get_toolset(server)
            tools_data = [tool.tool_spec for tool in toolset.tools]

            if not tools_data:
                return []

            # 获取现有工具的名称
            existing_tools = await MCPTool.filter(server=server).all()
            existing_tool_names = {tool.name for tool in existing_tools}

            # 获取新工具的名称
            new_tool_names = {tool_data["name"] for tool_data in tools_data}

            # 删除不再存在的工具
            tools_to_delete = existing_tool_names - new_tool_names
            if tools_to_delete:
                await MCPTool.filter(
                    server=server, name__in=list(tools_to_delete)
                ).delete()

            # 更新或创建工具
            created_tools = []
            for tool_data in tools_data:
                tool, _ = await MCPTool.update_or_create(
                    server=server,
                    name=tool_data["name"],
                    defaults={
                        "description": tool_data.get("description", ""),
                        "input_schema": tool_data.get("parameters"),
                        "output_schema": tool_data.get("outputSchema"),
                        "is_active": True,
                    },
                )
                created_tools.append(tool)

            return created_tools

        except Exception as e:
            # 记录错误，但不阻止服务器创建
            logger.error(f"Failed to sync tools for server {server.name}: {e}")
            return []


api_service = APIToolService()
mcp_service = MCPService()
