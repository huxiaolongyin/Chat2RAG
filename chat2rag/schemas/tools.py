from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from chat2rag.core.enums import ToolMethod


# APITool Schemas
class APIToolBase(BaseModel):
    name: str = Field(..., max_length=255, description="工具名称")
    description: Optional[str] = Field(None, description="工具描述")
    url: Optional[str] = Field(None, description="API URL")
    method: Optional[str] = Field(None, description="HTTP方法")
    parameters: Optional[Dict[str, Any]] = Field(None, description="请求参数")


class APIToolCreate(APIToolBase):
    pass


class APIToolUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255, description="工具名称")
    description: Optional[str] = Field(None, description="工具描述")
    url: Optional[str] = Field(None, description="API URL")
    method: Optional[str] = Field(None, description="HTTP方法")
    parameters: Optional[Dict[str, Any]] = Field(None, description="请求参数")


# MCPServer Schemas
class MCPServerBase(BaseModel):
    name: str = Field(..., max_length=100, description="服务器名称")
    mcp_type: str = Field(..., description="MCP类型", alias="mcpType")
    url: Optional[str] = Field(None, description="服务器URL")
    command: Optional[str] = Field(None, max_length=255, description="启动命令")
    args: Optional[List[str]] = Field(None, description="命令参数")
    env: Optional[Dict[str, str]] = Field(None, description="环境变量")
    is_active: bool = Field(True, description="是否启用", alias="isActive")


class MCPServerCreate(MCPServerBase):
    pass


class MCPServerUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="服务器名称")
    mcp_type: Optional[str] = Field(None, description="MCP类型", alias="mcpType")
    url: Optional[str] = Field(None, description="服务器URL")
    command: Optional[str] = Field(None, max_length=255, description="启动命令")
    args: Optional[List[str]] = Field(None, description="命令参数")
    env: Optional[Dict[str, str]] = Field(None, description="环境变量")
    is_active: Optional[bool] = Field(None, description="是否启用", alias="isActive")


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
