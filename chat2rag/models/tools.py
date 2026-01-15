from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import requests
from tortoise import fields

from chat2rag.core.enums import MCPToolType, Status, ToolMethod
from chat2rag.core.logger import get_logger

from .base import BaseModel, TimestampMixin

logger = get_logger(__name__)


class APITool(BaseModel, TimestampMixin):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    url = fields.TextField(null=True)
    method = fields.CharEnumField(ToolMethod, null=True)
    parameters = fields.JSONField(null=True)
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "api_tools"


class MCPServer(BaseModel, TimestampMixin):
    """MCP服务器配置"""

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100, unique=True, description="服务器名称")
    mcp_type = fields.CharEnumField(MCPToolType, default=MCPToolType.STREAMABLE)
    url = fields.TextField(null=True)
    command = fields.CharField(max_length=255, null=True, description="启动命令")
    args = fields.JSONField(default=list, null=True, description="命令参数")
    env = fields.JSONField(default=dict, null=True, description="环境变量")
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "mcp_servers"


class MCPTool(BaseModel, TimestampMixin):
    """MCP工具定义"""

    id = fields.IntField(primary_key=True)
    server = fields.ForeignKeyField("app_system.MCPServer", related_name="tools", on_delete=fields.CASCADE)
    name = fields.CharField(max_length=100, description="工具名称")
    description = fields.TextField(description="工具描述")
    input_schema = fields.JSONField(null=True, description="输入schema")
    output_schema = fields.JSONField(null=True, description="输出schema")
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "mcp_tools"
        unique_together = (("server", "name"),)


# class CustomTool(BaseModel, TimestampMixin):

#     id = fields.IntField(primary_key=True)
#     type = fields.CharEnumField(ToolType, default=ToolType.API)
#     name = fields.CharField(max_length=255)
#     display_name = fields.CharField(max_length=255, null=True)
#     description = fields.TextField(null=True)
#     url = fields.TextField(null=True)
#     method = fields.CharEnumField(ToolMethod, null=True)
#     parameters = fields.JSONField(null=True)
#     command = fields.TextField(null=True)
#     status = fields.IntEnumField(Status, default=Status.ENABLED)
#     customization = fields.JSONField(
#         null=True, description="存储工具的自定义信息，如中文名称、标签等"
#     )

#     class Meta:
#         table = "tools"

#     def to_dict(self) -> List[Dict] | Dict[str, Any]:
#         """
#         Convert the tool to a unified dictionary format. If it is an API, output a dict; if it is SSE or STDIO or Streamable, output a list
#         """
#         if self.type == ToolType.API:
#             return {
#                 "id": self.id,
#                 "type": self._get_enum_value(self.type),
#                 "function": {
#                     "name": self.name or "",
#                     "description": self.description or "",
#                     "url": self.url or "",
#                     "method": self._get_enum_value(self.method),
#                     "parameters": self._format_parameters(),
#                     "command": self.command or "",
#                 },
#                 "status": self._get_status_value(),
#                 "createTime": self._format_datetime(self.create_time),
#                 "updateTime": self._format_datetime(self.update_time),
#             }
#         else:
#             result = []
#             mcp_tools = self._fetch_mcp_tools()
#             for i, mcp_tool in enumerate(mcp_tools):
#                 result.append(
#                     {
#                         "id": f"{self.id}-{i+1}",
#                         "type": self._get_enum_value(self.type),
#                         "function": {
#                             "name": mcp_tool.name or "",
#                             "description": mcp_tool.description or "",
#                             "url": self.url or "",
#                             "method": "",
#                             "parameters": mcp_tool.parameters,
#                             "command": self.command or "",
#                         },
#                         "status": self._get_status_value(),
#                         "createTime": self._format_datetime(self.create_time),
#                         "updateTime": self._format_datetime(self.update_time),
#                     }
#                 )

#             return result

#     def _get_enum_value(self, enum_obj: Optional[Enum]) -> str:
#         """
#         Safely obtain enumeration values
#         """
#         return enum_obj.value if enum_obj else ""

#     def _get_status_value(self) -> str:
#         """
#         Obtain the status value. If it is ENABLED, return an empty string to match the API response format
#         """
#         if self.status == Status.ENABLED:
#             return ""
#         return self._get_enum_value(self.status)

#     def _format_datetime(self, dt: Optional[datetime]) -> str:
#         """
#         Format date and time
#         """
#         return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""

#     def _format_parameters(self) -> Dict[str, Any]:
#         """
#         Format parameters
#         """
#         if not self.parameters:
#             return {"properties": {}, "required": [], "type": "object"}

#         if isinstance(self.parameters, dict):
#             return self.parameters

#         return {"properties": {}, "required": [], "type": "object"}

#     def _create_api_function(self, name: str, url: str, method: str):
#         """
#         Create a function that calls an API

#         Args:
#             name: Function name
#             url: API URL
#             method: HTTP method (GET or POST)

#         Returns:
#             API calling function
#         """

#         def api_function(**kwargs):
#             try:
#                 if method.upper() == "GET":
#                     response = requests.get(url, params=kwargs)
#                 elif method.upper() == "POST":
#                     response = requests.post(url, json=kwargs)
#                 else:
#                     raise ValueError(f"Unsupported HTTP method: {method}")

#                 response.raise_for_status()
#                 return response.json()

#             except Exception as e:
#                 logger.error("API call failed, name: %s, Error info: %s", name, str(e))
#                 return ({"error": str(e)},)

#         # Set function name
#         api_function.__name__ = name

#         return api_function

#     def _fetch_api_tools(self):
#         """
#         Obtain API tool information based on the tool type
#         """
#         from haystack.tools import Tool, Toolset

#         logger.debug("Obtain information about API tools: %s", self.name)
#         return Toolset(
#             tools=[
#                 Tool(
#                     name=self.name,
#                     description=self.description,
#                     parameters=self.parameters,
#                     function=self._create_api_function(
#                         name=self.name, url=self.url, method=self.method
#                     ),
#                 )
#             ],
#         )

#     def _fetch_mcp_tools(self):
#         """
#         Obtain the MCP tool information based on the tool type
#         """
#         from haystack_integrations.tools.mcp import (
#             MCPToolset,
#             SSEServerInfo,
#             StdioServerInfo,
#             StreamableHttpServerInfo,
#         )

#         logger.debug("Obtain information about MCP tools: %s", self.name)

#         try:
#             # Connect the MCP SSE service
#             if self.type == ToolType.SSE and self.url:
#                 server_info = SSEServerInfo(self.url)

#             # Connect to the STDIO service
#             elif self.type == ToolType.STDIO and self.command:
#                 server_info = StdioServerInfo(self.command)

#             # Connect the Streamable service
#             elif self.type == ToolType.STREAMABLE and self.url:
#                 server_info = StreamableHttpServerInfo(self.url)

#             toolset = MCPToolset(server_info=server_info)
#             return toolset

#         except Exception as e:
#             logger.error(f"Error fetching MCP tools: {e}")
#             raise e
