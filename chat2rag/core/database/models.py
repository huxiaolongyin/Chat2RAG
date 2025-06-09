from datetime import datetime
from typing import Any, Dict, List, Optional

from haystack.tools import Tool
from haystack_integrations.tools.mcp import MCPToolset, SSEServerInfo, StdioServerInfo
from sqlalchemy import JSON, Column, DateTime, Enum, Float, Integer, String

from chat2rag.logger import get_logger

from .database import Base, create_all_tables
from .enums import Status, ToolMethod, ToolType

logger = get_logger(__name__)


class RAGPipelineMetrics(Base):
    __tablename__ = "rag_pipeline_metrics"

    time = Column(DateTime(timezone=True), primary_key=True)
    chat_id = Column(String)
    question = Column(String, nullable=False)
    answer = Column(String)
    document_ms = Column(Float)
    function_ms = Column(Float)
    rag_response_ms = Column(Float)
    total_ms = Column(Float)
    document_count = Column(Integer)
    question_tokens = Column(Integer)
    status = Column(String)


class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True)
    prompt_name = Column(String)
    prompt_intro = Column(String)
    prompt_text = Column(String)
    create_time = Column(DateTime(timezone=True), default=datetime.now())
    update_time = Column(
        DateTime(timezone=True), default=datetime.now(), onupdate=datetime.now()
    )

    def to_dict(self):
        return {
            "id": self.id,
            "prompt_name": self.prompt_name,
            "prompt_intro": self.prompt_intro,
            "prompt_text": self.prompt_text,
            "create_time": (
                self.create_time.strftime("%Y-%m-%d %H:%M:%S")
                if self.create_time
                else None
            ),
            "update_time": (
                self.update_time.strftime("%Y-%m-%d %H:%M:%S")
                if self.update_time
                else None
            ),
        }


class MCPTool(Base):
    __tablename__ = "tools"

    id = Column(Integer, primary_key=True)
    type = Column(Enum(ToolType))
    name = Column(String)
    description = Column(String, nullable=True)
    url = Column(String, nullable=True)
    method = Column(Enum(ToolMethod), nullable=True)
    parameters = Column(JSON, nullable=True)
    command = Column(String, nullable=True)
    status = Column(Enum(Status), default=Status.ENABLED)
    create_time = Column(DateTime(timezone=True), default=datetime.now())
    update_time = Column(
        DateTime(timezone=True), default=datetime.now(), onupdate=datetime.now()
    )

    def to_dict(self) -> List[Dict] | Dict[str, Any]:
        """将工具转换为统一的字典格式，如果是API则输出dict，如果是SSE或STDIO则输出list"""
        if self.type == ToolType.API:
            return {
                "id": self.id,
                "type": self._get_enum_value(self.type),
                "function": {
                    "name": self.name or "",
                    "description": self.description or "",
                    "url": self.url or "",
                    "method": self._get_enum_value(self.method),
                    "parameters": self._format_parameters(),
                    "command": self.command or "",
                },
                "status": self._get_status_value(),
                "createTime": self._format_datetime(self.create_time),
                "updateTime": self._format_datetime(self.update_time),
            }
        else:
            result = []
            mcp_tools = self._fetch_mcp_tools()
            for i, mcp_tool in enumerate(mcp_tools):
                result.append(
                    {
                        "id": f"{self.id}-{i+1}",
                        "type": self._get_enum_value(self.type),
                        "function": {
                            "name": mcp_tool.name or "",
                            "description": mcp_tool.description or "",
                            "url": self.url or "",
                            "method": "",
                            "parameters": mcp_tool.parameters,
                            "command": self.command or "",
                        },
                        "status": self._get_status_value(),
                        "createTime": self._format_datetime(self.create_time),
                        "updateTime": self._format_datetime(self.update_time),
                    }
                )

            return result

    def _get_enum_value(self, enum_obj: Optional[Enum]) -> str:
        """安全地获取枚举值"""
        return enum_obj.value if enum_obj else ""

    def _get_status_value(self) -> str:
        """获取状态值，如果是ENABLED返回空字符串匹配API响应格式"""
        if self.status == Status.ENABLED:
            return ""
        return self._get_enum_value(self.status)

    def _format_datetime(self, dt: Optional[datetime]) -> str:
        """格式化日期时间"""
        return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""

    def _format_parameters(self) -> Dict[str, Any]:
        """格式化参数"""
        if not self.parameters:
            return {"properties": {}, "required": [], "type": "object"}

        if isinstance(self.parameters, dict):
            return self.parameters

        return {"properties": {}, "required": [], "type": "object"}

    def _fetch_mcp_tools(self) -> List[Tool]:
        """根据工具类型获取MCP工具信息"""
        try:
            if self.type == ToolType.SSE and self.url:
                server_info = SSEServerInfo(self.url)
            elif self.type == ToolType.STDIO and self.command:
                server_info = StdioServerInfo(self.command)

            return MCPToolset(server_info=server_info).tools

        except Exception as e:
            logger.error(f"Error fetching MCP tools: {e}")
            return []


create_all_tables()
