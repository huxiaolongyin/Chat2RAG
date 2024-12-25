from pydantic import BaseModel, Field
from typing import Dict, Optional, List


class ToolParameter(BaseModel):
    type: str = Field(..., description="参数类型")
    description: Optional[str] = Field(None, description="参数描述")


class ToolParameters(BaseModel):
    type: str = Field("object", description="参数对象类型")
    properties: Dict[str, ToolParameter] = Field(..., description="参数属性列表")
    required: Optional[List[str]] = Field(None, description="必需参数列表")


class ToolFunction(BaseModel):
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    url: str = Field(..., description="API接口地址")
    method: str = Field("GET", description="HTTP请求方法")
    parameters: Optional[ToolParameters] = Field(None, description="工具参数配置")


class ToolConfig(BaseModel):
    function: ToolFunction = Field(..., description="工具函数配置")
