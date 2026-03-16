import asyncio
from functools import lru_cache
from typing import Any, Dict, List, Set, Tuple

from tortoise.expressions import Q
from tortoise.transactions import in_transaction

import chat2rag.tools as tools_module
from chat2rag.core.crud import CRUDBase
from chat2rag.core.enums import SortOrder
from chat2rag.core.exceptions import (
    MCPConnectionError,
    ParameterException,
    ToolServiceError,
    ToolSyncError,
    ValueAlreadyExist,
    ValueNoExist,
)
from chat2rag.core.logger import get_logger
from chat2rag.models import APITool, MCPServer, MCPTool
from chat2rag.schemas.tools import (
    APIToolCreate,
    APIToolCreateRequest,
    APIToolUpdate,
    APIToolUpdateRequest,
    CombinedCreateRequest,
    CombinedUpdateRequest,
    MCPServerCreate,
    MCPServerCreateRequest,
    MCPServerUpdate,
    MCPServerUpdateRequest,
)
from chat2rag.tools.mcp import connection_manager

logger = get_logger(__name__)

# 配置常量
DEFAULT_PAGE_SIZE = 10
MAX_RETRY_ATTEMPTS = 3
TOOL_SYNC_TIMEOUT = 30


class APIToolService(CRUDBase[APITool, APIToolCreate, APIToolUpdate]):
    """API工具服务"""

    def __init__(self):
        super().__init__(APITool)


class MCPService(CRUDBase[MCPServer, MCPServerCreate, MCPServerUpdate]):
    """MCP服务管理"""

    def __init__(self):
        super().__init__(MCPServer)
        self._tool_registry_cache: Dict[str, Any] | None = None

    @lru_cache(maxsize=1)
    def _get_builtin_tool_registry(self) -> Dict[str, Any]:
        """获取内置工具注册表（带缓存）"""
        tool_registry = {}

        if hasattr(tools_module, "__all__"):
            for tool_name in tools_module.__all__:
                if hasattr(tools_module, tool_name):
                    tool_instance = getattr(tools_module, tool_name)
                    tool_registry[tool_name] = tool_instance

        logger.info(f"Loaded {len(tool_registry)} builtin tools")
        logger.debug(f"Builtin tool names: {list(tool_registry.keys())}")
        return tool_registry

    async def get_by_names(self, names: List[str]) -> Tuple[List[Any], Dict[str, str]]:
        """根据名称获取工具列表（内置工具 + MCP工具）

        Args:
            names: 工具名称列表

        Returns:
            (工具列表, {工具名称: MCP服务器名称})

        Raises:
            ToolServiceError: 获取工具时发生错误
        """
        if not names:
            return [], {}

        all_tools = []
        tool_sources: Dict[str, str] = {}

        try:
            builtin_tools = self._get_builtin_tools_by_names(names)
            all_tools.extend(builtin_tools)

            mcp_tools, mcp_tool_sources = await self._get_mcp_tools_by_names(names)
            all_tools.extend(mcp_tools)
            tool_sources.update(mcp_tool_sources)

            logger.info(f"Retrieved {len(all_tools)} tools for names={names}")
            return all_tools, tool_sources

        except Exception as e:
            logger.exception(f"Failed to get tools by names: {names}")
            raise ToolServiceError(f"Failed to get tools: {e}") from e

    def _get_builtin_tools_by_names(self, names: List[str]) -> List[Any]:
        """获取内置工具"""
        tool_registry = self._get_builtin_tool_registry()
        builtin_tools = []

        for name in names:
            if name in tool_registry:
                builtin_tools.append(tool_registry[name])
            else:
                logger.debug(f"Builtin tool '{name}' not found")

        return builtin_tools

    async def _get_mcp_tools_by_names(
        self, names: List[str]
    ) -> Tuple[List[Any], Dict[str, str]]:
        """获取MCP工具

        Returns:
            (工具列表, {工具名称: MCP服务器名称})
        """
        try:
            mcp_tools = (
                await MCPTool.filter(name__in=names, is_active=True)
                .prefetch_related("server")
                .all()
            )

            if not mcp_tools:
                return [], {}

            tool_sources = {tool.name: tool.server.name for tool in mcp_tools}

            servers_tools = self._group_tools_by_server(mcp_tools)

            all_mcp_tools = []
            tasks = [
                self._get_server_tools(server, tool_names, names)
                for server, tool_names in servers_tools.items()
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Failed to get server tools: {result}")
                    continue
                all_mcp_tools.extend(result)

            return all_mcp_tools, tool_sources

        except Exception as e:
            logger.exception("Failed to get MCP tools")
            return [], {}

    def _group_tools_by_server(
        self, mcp_tools: List[MCPTool]
    ) -> Dict[MCPServer, Set[str]]:
        """按服务器分组工具"""
        servers_tools: Dict[MCPServer, Set[str]] = {}

        for tool in mcp_tools:
            if tool.server not in servers_tools:
                servers_tools[tool.server] = set()
            servers_tools[tool.server].add(tool.name)

        return servers_tools

    async def _get_server_tools(
        self, server: MCPServer, tool_names: Set[str], requested_names: List[str]
    ) -> List[Any]:
        """获取指定服务器的工具"""
        try:
            if not server.is_active:
                logger.warning(f"Server '{server.name}' is inactive")
                return []

            toolset = await asyncio.wait_for(
                connection_manager.get_toolset(server), timeout=TOOL_SYNC_TIMEOUT
            )

            # 只返回请求的工具
            matched_tools = [
                tool
                for tool in toolset.tools
                if tool.name in requested_names and tool.name in tool_names
            ]

            logger.debug(
                f"Retrieved {len(matched_tools)} tools from server '{server.name}'"
            )
            return matched_tools

        except asyncio.TimeoutError:
            logger.error(f"Timeout connecting to server {server.name}")
            raise MCPConnectionError(f"Connection timeout for server {server.name}")
        except Exception as e:
            logger.error(f"Error connecting to server {server.name}: {e}")
            raise MCPConnectionError(f"Failed to connect to server {server.name}: {e}")

    async def get_mcp_tool_list(
        self,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        search: Q | None = None,
        order: List[str] | None = None,
    ) -> Tuple[int, List[MCPTool]]:
        """获取MCP工具列表（分页）

        Args:
            page: 页码
            page_size: 每页大小
            search: 搜索条件
            order: 排序字段

        Returns:
            (总数, 工具列表)
        """
        try:
            query = MCPTool.all().prefetch_related("server")

            if search:
                query = query.filter(search)

            # 获取总数
            total = await query.count()

            # 排序
            if order:
                query = query.order_by(*order)
            else:
                query = query.order_by("-created_at")

            # 分页
            offset = (page - 1) * page_size
            tools = await query.offset(offset).limit(page_size).all()
            total_pages = page / (total + page_size - 1) // page_size

            logger.info(
                f"Retrieved {len(tools)} MCP tools: page={page}, total_pages={total_pages}"
            )
            return total, tools

        except Exception as e:
            logger.error(f"Error getting MCP tool list: {e}")
            raise ToolServiceError(f"Failed to get MCP tool list: {e}") from e

    async def create(
        self, obj_in: MCPServerCreate, exclude: List[str] | None = None
    ) -> MCPServer:
        """创建MCP服务器并同步工具"""
        try:
            async with in_transaction():
                mcp_server = await super().create(obj_in, exclude)

                # 如果服务器启用，则同步工具
                if mcp_server.is_active:
                    await self._sync_tools_with_retry(mcp_server)

                logger.info(f"MCP server created: name='{mcp_server.name}'")
                return mcp_server

        except Exception as e:
            logger.error(f"Error creating MCP server: {e}")
            raise ToolServiceError(f"Failed to create MCP server: {e}") from e

    async def update(
        self, id: int, obj_in: MCPServerUpdate, exclude: List[str] | None = None
    ) -> MCPServer | None:
        """更新MCP服务器"""
        try:
            old_server = await self.get(id)
            if not old_server:
                logger.warning(f"MCP server with id {id} not found")
                return None

            async with in_transaction():
                server = await super().update(id, obj_in, exclude)

                # 检查是否需要重新同步工具
                if self._should_resync_tools(obj_in):
                    await self._sync_tools_with_retry(server)
                elif hasattr(obj_in, "is_active") and not obj_in.is_active:
                    # 禁用服务器时，禁用所有工具
                    await MCPTool.filter(server=server).update(is_active=False)
                    logger.info(f"Disabled all tools: server='{server.name}'")

                logger.info(f"MCP server updated: name='{server.name}'")
                return server

        except Exception as e:
            logger.error(f"Error updating MCP server {id}: {e}")
            raise ToolServiceError(f"Failed to update MCP server: {e}") from e

    def _should_resync_tools(self, obj_in: MCPServerUpdate) -> bool:
        """检查是否需要重新同步工具"""
        config_fields = ["url", "command", "args", "env", "mcp_type"]
        config_changed = any(
            hasattr(obj_in, attr) and getattr(obj_in, attr) is not None
            for attr in config_fields
        )

        is_activated = hasattr(obj_in, "is_active") and obj_in.is_active

        return config_changed or is_activated

    async def remove(self, id: int) -> bool:
        """删除MCP服务器及其所有工具"""
        try:
            server = await self.get(id)
            if not server:
                logger.warning(f"MCP server with id {id} not found")
                return False

            async with in_transaction():
                # 删除所有关联的工具
                deleted_tools = await MCPTool.filter(server=server).delete()
                logger.info(
                    f"Tools deleted: count={deleted_tools}, server='{server.name}'"
                )

                # 删除服务器
                result = await super().remove(id)

                if result:
                    logger.info(f"MCP server deleted: name='{server.name}'")

                return result

        except Exception as e:
            logger.exception(f"MCP server {id} deleted error")
            raise ToolServiceError(f"Failed to remove MCP server: {e}") from e

    async def sync_tools(self, server_id: int) -> List[MCPTool]:
        """手动同步指定服务器的工具"""

        server = await self.get(server_id)
        tools = await self._sync_tools_with_retry(server)
        logger.info(f"Tools synced: count={len(tools)}, server='{server.name}'")
        return tools

    async def _sync_tools_with_retry(self, server: MCPServer) -> List[MCPTool]:
        """带重试的工具同步"""
        last_error = None

        for attempt in range(MAX_RETRY_ATTEMPTS):
            try:
                return await self._sync_tools(server)
            except Exception as e:
                last_error = e
                if attempt < MAX_RETRY_ATTEMPTS - 1:
                    wait_time = 2**attempt  # 指数退避
                    logger.warning(
                        f"Tool sync attempt {attempt + 1} failed for {server.name}, retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"All {MAX_RETRY_ATTEMPTS} sync attempts failed for {server.name}"
                    )

        raise ToolSyncError(
            f"Failed to sync tools after {MAX_RETRY_ATTEMPTS} attempts: {last_error}"
        )

    async def _sync_tools(self, server: MCPServer) -> List[MCPTool]:
        """从MCP服务器同步工具到数据库"""
        try:
            if not server.is_active or not server.url:
                logger.debug(f"Skipping tool sync for inactive server {server.name}")
                return []

            # 获取工具集
            toolset = await asyncio.wait_for(
                connection_manager.get_toolset(server), timeout=TOOL_SYNC_TIMEOUT
            )

            tools_data = [tool.tool_spec for tool in toolset.tools]

            if not tools_data:
                logger.info(f"No tools found: server='{server.name}'")
                return []

            # 使用事务确保数据一致性
            async with in_transaction():
                return await self._update_server_tools(server, tools_data)

        except asyncio.TimeoutError:
            raise ToolSyncError(f"Timeout syncing tools for server {server.name}")
        except Exception as e:
            raise ToolSyncError(f"Failed to sync tools for server {server.name}: {e}")

    async def _update_server_tools(
        self, server: MCPServer, tools_data: List[Dict[str, Any]]
    ) -> List[MCPTool]:
        """更新服务器的工具列表"""
        # 获取现有工具
        existing_tools = await MCPTool.filter(server=server).all()
        existing_tool_names = {tool.name for tool in existing_tools}

        # 获取新工具名称
        new_tool_names = {tool_data["name"] for tool_data in tools_data}

        # 删除不再存在的工具
        tools_to_delete = existing_tool_names - new_tool_names
        if tools_to_delete:
            deleted_count = await MCPTool.filter(
                server=server, name__in=list(tools_to_delete)
            ).delete()
            logger.info(
                f"Deleted {deleted_count} obsolete tools for server {server.name}"
            )

        # 批量更新或创建工具
        created_tools = []
        for tool_data in tools_data:
            tool, created = await MCPTool.update_or_create(
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

            if created:
                logger.debug(f"Created new tool: {tool.name}")
            else:
                logger.debug(f"Updated existing tool: {tool.name}")

        logger.info(f"Tools synced: count={len(created_tools)}, server='{server.name}'")
        return created_tools


class ToolService:
    async def create(self, request: CombinedCreateRequest):
        if isinstance(request, APIToolCreateRequest):
            if await APITool.filter(name=request.data.name).exists():
                raise ValueAlreadyExist("工具名已存在")
            return await api_service.create(request.data)

        elif isinstance(request, MCPServerCreateRequest):
            if await MCPServer.filter(name=request.data.name).exists():
                raise ValueAlreadyExist("工具名已存在")

            return await mcp_service.create(request.data)

    async def update(
        self, tool_id: int, tool_type: str, request: CombinedUpdateRequest
    ):
        if tool_type == "api":
            if not isinstance(request, APIToolUpdateRequest):
                raise ParameterException(msg="API工具输入参数错误")

            await api_service.get(tool_id)

            # 检查名称是否已被其他工具使用
            if request.data.name:
                if (
                    await APITool.filter(name=request.data.name)
                    .exclude(id=tool_id)
                    .exists()
                ):
                    raise ValueAlreadyExist("工具名已存在")

            return await api_service.update(tool_id, request.data)

        elif tool_type == "mcp":
            if not isinstance(request, MCPServerUpdateRequest):
                raise ParameterException(msg="MCP工具输入参数错误")
            await mcp_service.get(tool_id)

            if request.data.name:
                if (
                    await MCPServer.filter(name=request.data.name)
                    .exclude(id=tool_id)
                    .exists()
                ):
                    raise ValueAlreadyExist("工具名已存在")

            return await mcp_service.update(tool_id, request.data)

    async def remove(self, tool_id: int, tool_type: str):
        if tool_type == "api":
            await api_service.get(tool_id)
            await api_service.remove(tool_id)
        else:
            if not await mcp_service.get(tool_id):
                raise ValueNoExist("工具不存在")
            await mcp_service.remove(tool_id)

    async def get(self, tool_id: int, tool_type: str):
        """获取工具详细信息"""
        if tool_type == "api":
            return await api_service.get(tool_id)

        elif tool_type == "mcp":
            tool = await MCPTool.filter(id=tool_id).prefetch_related("server").first()
            if not tool:
                raise ValueNoExist("工具不存在")
            return tool

    async def get_list(
        self,
        page: int,
        page_size: int,
        tool_type: str,
        search: Q = Q(),
        order: list[str] | None = None,
    ) -> Tuple[int, list]:
        tool_list = []
        total = 0

        if tool_type in ["api", "all"]:
            # 获取API工具
            api_total, api_tools = await api_service.get_list(1, 999, search, order)
            tool_list.extend(
                [{**await tool.to_dict(), "tool_type": "api"} for tool in api_tools]
            )
            total += api_total

        if tool_type in ["mcp", "all"]:
            # 获取MCP工具
            mcp_total, mcp_tools = await mcp_service.get_mcp_tool_list(
                1, 999, search, order
            )
            tool_list.extend(
                [{**await tool.to_dict(), "tool_type": "mcp"} for tool in mcp_tools]
            )
            total += mcp_total

        # 如果是获取全部工具，需要重新排序和分页
        if tool_type == "all":
            # 合并后重新排序（根据order参数判断升降序）
            reverse = order and order[0].startswith("-")
            sort_key = order[0].replace("-", "")
            tool_list.sort(key=lambda x: x.get(sort_key, ""), reverse=reverse)

            # 重新分页
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            tool_list = tool_list[start_idx:end_idx]

        return total, tool_list


# 服务实例
api_service = APIToolService()
mcp_service = MCPService()
tool_service = ToolService()
