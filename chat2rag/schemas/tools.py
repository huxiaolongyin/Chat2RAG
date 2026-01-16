from typing import Any, Dict, List, Literal, Union

from pydantic import BaseModel, Field

from chat2rag.core.enums import SortOrder, ToolMethod, ToolSortField, ToolType

from .base import BaseSchema, IDMixin, TimestampMixin
from .common import Current, Size


class ToolQueryParams(BaseSchema):
    """工具检索字段"""

    current: Current = 1
    size: Size = 10
    tool_type: ToolType = Field(ToolType.ALL, description="工具类型")
    tool_name: str | None = Field(None, description="工具名称")
    tool_desc: str | None = Field(None, description="工具描述")
    is_active: bool | None = Field(None, description="是否启用")
    sort_by: ToolSortField = Field(ToolSortField.CREATE_TIME, description="排序字段")
    sort_order: SortOrder = Field(SortOrder.DESC, description="排序方向(asc, desc)，默认 desc")


# APITool Schemas
class APIToolBase(BaseModel):
    name: str = Field(..., max_length=255, description="工具名称")
    description: str | None = Field(None, description="工具描述")
    url: str | None = Field(None, description="API URL")
    method: str | None = Field(None, description="HTTP方法")
    parameters: Dict[str, Any] | None = Field(None, description="请求参数")


class ToolData(BaseSchema, IDMixin, TimestampMixin):
    name: str = Field(..., description="工具名称")
    description: str | None = Field(None, description="工具描述")
    tool_type: ToolType = Field(..., description="工具类型")
    is_active: bool = Field(..., description="是否启用")
    command: str | None = Field(None, description="MCP工具stdio方式使用的命令")
    args: list | None = Field(None, description="MCP工具stdio方式使用的命令参数")
    url: str | None = Field(None, description="API或MCP工具请求的地址")
    method: ToolMethod | None = Field(None, description="API工具的请求类型")
    parameters: Dict[str, Any] | None = Field(None, description="API请求参数")
    server_id: int | None = Field(None, description="MCP服务ID")
    input_schema: dict | None = Field(None, description="输入格式")
    output_schema: dict | None = Field(None, description="输出格式")


class ToolSyncData(BaseSchema):
    """工具同步数据"""

    server_id: int
    tool_count: int
    tools: List[ToolData]


class APIToolCreate(APIToolBase): ...


class APIToolUpdate(BaseModel):
    name: str | None = Field(None, max_length=255, description="工具名称")
    description: str | None = Field(None, description="工具描述")
    url: str | None = Field(None, description="API URL")
    method: str | None = Field(None, description="HTTP方法")
    parameters: Dict[str, Any] | None = Field(None, description="请求参数")


# MCPServer Schemas
class MCPServerBase(BaseModel):
    name: str = Field(..., max_length=100, description="服务器名称")
    mcp_type: str = Field(..., description="MCP类型", alias="mcpType")
    url: str | None = Field(None, description="服务器URL")
    command: str | None = Field(None, max_length=255, description="启动命令")
    args: List[str] | None = Field(None, description="命令参数")
    env: Dict[str, str] | None = Field(None, description="环境变量")
    is_active: bool = Field(True, description="是否启用", alias="isActive")


class MCPServerCreate(MCPServerBase):
    pass


class MCPServerUpdate(BaseModel):
    name: str | None = Field(None, max_length=100, description="服务器名称")
    mcp_type: str | None = Field(None, description="MCP类型", alias="mcpType")
    url: str | None = Field(None, description="服务器URL")
    command: str | None = Field(None, max_length=255, description="启动命令")
    args: List[str] | None = Field(None, description="命令参数")
    env: Dict[str, str] | None = Field(None, description="环境变量")
    is_active: bool | None = Field(None, description="是否启用", alias="isActive")


class APIToolCreateRequest(BaseModel):
    tool_type: Literal["api"] = Field("api", alias="toolType")
    data: APIToolCreate


class MCPServerCreateRequest(BaseModel):
    tool_type: Literal["mcp"] = Field("mcp", alias="toolType")
    data: MCPServerCreate


class APIToolUpdateRequest(BaseModel):
    tool_type: Literal["api"] = Field("api", alias="toolType")
    data: APIToolUpdate


class MCPServerUpdateRequest(BaseModel):
    tool_type: Literal["mcp"] = Field("mcp", alias="toolType")
    data: MCPServerUpdate


CombinedCreateRequest = Union[APIToolCreateRequest, MCPServerCreateRequest]
CombinedUpdateRequest = Union[APIToolUpdateRequest, MCPServerUpdateRequest]
