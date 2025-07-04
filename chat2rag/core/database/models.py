from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import requests
from haystack.tools import Tool, Toolset
from haystack_integrations.tools.mcp import (
    MCPToolset,
    SSEServerInfo,
    StdioServerInfo,
    StreamableHttpServerInfo,
)
from sqlalchemy import JSON, Column, DateTime, Enum, Float, Integer, String

from chat2rag.enums import Status, ToolMethod, ToolType
from chat2rag.logger import get_logger

from .database import Base, create_all_tables

logger = get_logger(__name__)


class PipelineMetrics(Base):
    __tablename__ = "pipeline_metrics"

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
    status = Column(Enum(Status), default=Status.ENABLED)


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


class CustomTool(Base):
    __tablename__ = "tools"

    id = Column(Integer, primary_key=True)
    type = Column(Enum(ToolType))
    name = Column(String)
    display_name = Column(String, nullable=True)
    description = Column(String, nullable=True)
    url = Column(String, nullable=True)
    method = Column(Enum(ToolMethod), nullable=True)
    parameters = Column(JSON, nullable=True)
    command = Column(String, nullable=True)
    status = Column(Enum(Status), default=Status.ENABLED)
    customization = Column(
        JSON, nullable=True, comment="存储工具的自定义信息，如中文名称、标签等"
    )
    create_time = Column(DateTime(timezone=True), default=datetime.now())
    update_time = Column(
        DateTime(timezone=True), default=datetime.now(), onupdate=datetime.now()
    )

    def to_dict(self) -> List[Dict] | Dict[str, Any]:
        """
        Convert the tool to a unified dictionary format. If it is an API, output a dict; if it is SSE or STDIO or Streamable, output a list
        """
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
        """
        Safely obtain enumeration values
        """
        return enum_obj.value if enum_obj else ""

    def _get_status_value(self) -> str:
        """
        Obtain the status value. If it is ENABLED, return an empty string to match the API response format
        """
        if self.status == Status.ENABLED:
            return ""
        return self._get_enum_value(self.status)

    def _format_datetime(self, dt: Optional[datetime]) -> str:
        """
        Format date and time
        """
        return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""

    def _format_parameters(self) -> Dict[str, Any]:
        """
        Format parameters
        """
        if not self.parameters:
            return {"properties": {}, "required": [], "type": "object"}

        if isinstance(self.parameters, dict):
            return self.parameters

        return {"properties": {}, "required": [], "type": "object"}

    def _create_api_function(self, name: str, url: str, method: str) -> Callable:
        """
        Create a function that calls an API

        Args:
            name: Function name
            url: API URL
            method: HTTP method (GET or POST)

        Returns:
            API calling function
        """

        def api_function(**kwargs):
            try:
                if method.upper() == "GET":
                    response = requests.get(url, params=kwargs)
                elif method.upper() == "POST":
                    response = requests.post(url, json=kwargs)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                return response.json()

            except Exception as e:
                logger.error("API call failed, name: %s, Error info: %s", name, str(e))
                return {"error": str(e)}

        # Set function name
        api_function.__name__ = name

        return api_function

    def _fetch_api_tools(self) -> Toolset:
        """
        Obtain API tool information based on the tool type
        """
        logger.debug("Obtain information about API tools: %s", self.name)
        return Toolset(
            tools=[
                Tool(
                    name=self.name,
                    description=self.description,
                    parameters=self.parameters,
                    function=self._create_api_function(
                        name=self.name, url=self.url, method=self.method
                    ),
                )
            ],
        )

    def _fetch_mcp_tools(self) -> MCPToolset:
        """
        Obtain the MCP tool information based on the tool type
        """
        logger.debug("Obtain information about MCP tools: %s", self.name)

        try:
            # Connect the MCP SSE service
            if self.type == ToolType.SSE and self.url:
                server_info = SSEServerInfo(self.url)

            # Connect to the STDIO service
            elif self.type == ToolType.STDIO and self.command:
                server_info = StdioServerInfo(self.command)

            # Connect the Streamable service
            elif self.type == ToolType.STREAMABLE and self.url:
                server_info = StreamableHttpServerInfo(self.url)

            toolset = MCPToolset(server_info=server_info)
            return toolset

        except Exception as e:
            logger.error(f"Error fetching MCP tools: {e}")
            raise e


create_all_tables()
