from typing import List

from haystack.tools import Tool

from chat2rag.database.connection import db_session
from chat2rag.database.models import CustomTool
from chat2rag.enums import Status, ToolType
from chat2rag.logger import get_logger
from chat2rag.tools.web_search import web_search

logger = get_logger(__name__)


class ToolManager:
    """
    Tool manager for API and MCP tools
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self.all_tools = self._fetch_all_tool()

    def _fetch_all_tool(self) -> List[Tool]:
        """
        Fetch all tools from database
        """

        all_tools = []

        with db_session() as db:
            # Build basic queries
            enabled_tools = (
                db.query(CustomTool).filter(CustomTool.status == Status.ENABLED).all()
            )

            for t in enabled_tools:
                if t.type == ToolType.API:
                    all_tools.extend(t._fetch_api_tools().tools)
                else:
                    all_tools.extend(t._fetch_mcp_tools().tools)

        if not all_tools:
            raise ValueError("No available tools were found")

        return all_tools

    def fetch_tools(self, select_tools: List[str]) -> List[Tool]:
        """
        Fetch tools from database

        Args:
            select_tools: The list of selected tools, ["all"] indicates obtaining all tools, and ["tool1", "tool2"] indicates obtaining the specified tools
        """
        if not select_tools:
            raise ValueError("No tools were specified")

        all_tool = self.all_tools + [web_search]

        logger.debug("A tool for obtaining choices: %s", select_tools)

        if "all" in select_tools or "ALL" in select_tools:
            return all_tool

        return [tool for tool in all_tool if tool.name in select_tools]


tool_manager = ToolManager()
