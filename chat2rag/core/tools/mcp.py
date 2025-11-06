from typing import Dict, Optional

from haystack_integrations.tools.mcp import (
    MCPToolset,
    SSEServerInfo,
    StdioServerInfo,
    StreamableHttpServerInfo,
)

from chat2rag.enums import MCPToolType
from chat2rag.logger import get_logger
from chat2rag.models import MCPServer

logger = get_logger(__name__)


class MCPConnectionManager:
    """管理MCP连接的生命周期"""

    # 单例模式
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MCPConnectionManager, cls).__new__(
                cls, *args, **kwargs
            )
        return cls._instance

    def __init__(self):
        self._toolsets: Dict[int, MCPToolset] = {}

    async def get_toolset(self, server: MCPServer) -> Optional[MCPToolset]:
        """获取或创建toolset"""
        # 如果已存在，直接返回
        if server.id in self._toolsets:
            return self._toolsets[server.id]

        try:
            # 根据不同类型创建 server_info
            if server.mcp_type == MCPToolType.SSE and server.url:
                server_info = SSEServerInfo(server.url)
            elif server.mcp_type == MCPToolType.STDIO and server.command:
                server_info = StdioServerInfo(server.command)
            elif server.mcp_type == MCPToolType.STREAMABLE and server.url:
                server_info = StreamableHttpServerInfo(server.url)
            else:
                return None

            # 创建并缓存toolset
            logger.debug(f"Connect to the MCP service: {server_info}")
            toolset = MCPToolset(server_info=server_info)
            self._toolsets[server.id] = toolset
            return toolset

        except Exception as e:
            logger.error(f"Error creating toolset for server {server.name}: {e}")
            return None

    async def remove_toolset(self, server_id: int):
        """移除并清理toolset"""
        if server_id in self._toolsets:
            toolset = self._toolsets.pop(server_id)

            # 如果toolset有cleanup方法，调用它
            if hasattr(toolset, "close"):
                try:
                    await toolset.close()
                except Exception as e:
                    logger.error(f"Error cleaning up toolset: {e}")

    async def cleanup_all(self):
        """清理所有连接"""
        for server_id in list(self._toolsets.keys()):
            await self.remove_toolset(server_id)
