from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from chat2rag.enums import ToolMethod, ToolType


class ToolParameter(BaseModel):
    type: str = Field(..., description="参数类型")
    description: Optional[str] = Field(None, description="参数描述")


class ToolParameters(BaseModel):
    type: str = Field("object", description="参数对象类型")
    properties: Dict[str, ToolParameter] = Field(..., description="参数属性列表")
    required: Optional[List[str]] = Field(None, description="必需参数列表")


class ToolFunction(BaseModel):
    type: ToolType = Field(ToolType.API, description="工具类型")
    name: str = Field(..., description="工具名称")
    display_name: Optional[str] = Field(
        None, description="工具显示名称", alias="displayName"
    )
    description: Optional[str] = Field(None, description="工具描述")
    url: Optional[str] = Field(None, description="API接口地址")
    method: Optional[ToolMethod] = Field(ToolMethod.NONE, description="HTTP请求方法")
    parameters: Optional[ToolParameters] = Field(None, description="工具参数配置")
    command: Optional[str] = Field(None, description="命令行命令")
    customization: Optional[Dict] = Field(None, description="工具自定义信息")


class ToolConfig(BaseModel):
    function: ToolFunction = Field(..., description="工具函数配置")
