import asyncio
from threading import Lock
from typing import Dict

from haystack_integrations.tools.mcp import (
    MCPToolset,
    SSEServerInfo,
    StdioServerInfo,
    StreamableHttpServerInfo,
)

from chat2rag.core.enums import MCPToolType
from chat2rag.core.logger import get_logger
from chat2rag.models import MCPServer

logger = get_logger(__name__)


class MCPConnectionManager:
    """管理MCP连接的生命周期"""

    # 单例模式
    _instance = None
    _lock = Lock()
    _initialized = False

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._toolsets: Dict[int, MCPToolset] = {}
                    self._locks: Dict[int, asyncio.Lock] = {}
                    MCPConnectionManager._initialized = True

    async def get_toolset(self, server: MCPServer) -> MCPToolset | None:
        """获取或创建toolset"""
        # 如果已存在，直接返回
        if server.id in self._toolsets:
            return self._toolsets[server.id]

        # 确保每个服务器只有一个锁
        if server.id not in self._locks:
            self._locks[server.id] = asyncio.Lock()

        async with self._locks[server.id]:
            # 双重检查，防止并发创建
            if server.id in self._toolsets:
                return self._toolsets[server.id]

            try:
                server_info = self._create_server_info(server)
                if not server_info:
                    return None

                logger.debug(f"Connecting to MCP service: {server.name} ({server_info})")
                toolset = MCPToolset(server_info=server_info, eager_connect=True)

                self._toolsets[server.id] = toolset
                logger.info(f"Successfully connected to MCP server: {server.name}")
                return toolset

            except Exception as e:
                logger.error(f"Failed to create toolset for server {server.name}: {e}", exc_info=True)
                return None

    def _create_server_info(self, server: MCPServer):
        """抽取server_info创建逻辑"""
        if server.mcp_type == MCPToolType.SSE and server.url:
            return SSEServerInfo(server.url)
        elif server.mcp_type == MCPToolType.STDIO and server.command:
            return StdioServerInfo(server.command)
        elif server.mcp_type == MCPToolType.STREAMABLE and server.url:
            return StreamableHttpServerInfo(server.url)
        else:
            logger.warning(f"Invalid server configuration: {server.name}")
            return None

    async def remove_toolset(self, server_id: int) -> bool:
        """移除并清理toolset"""
        if server_id not in self._toolsets:
            return False

        toolset = self._toolsets.pop(server_id)

        try:
            # 尝试多种清理方法
            if hasattr(toolset, "close"):
                await toolset.close()
            elif hasattr(toolset, "cleanup"):
                await toolset.cleanup()
            elif hasattr(toolset, "disconnect"):
                await toolset.disconnect()

            logger.debug(f"Successfully cleaned up toolset for server {server_id}")
            return True

        except Exception as e:
            logger.error(f"Error cleaning up toolset for server {server_id}: {e}", exc_info=True)
            return False
        finally:
            # 清理锁
            self._locks.pop(server_id, None)

    async def cleanup_all(self):
        """清理所有连接"""
        for server_id in list(self._toolsets.keys()):
            await self.remove_toolset(server_id)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup_all()


connection_manager = MCPConnectionManager()
