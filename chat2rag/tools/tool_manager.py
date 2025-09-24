from contextlib import contextmanager
from typing import Generator, List

from haystack.tools import Tool
from sqlalchemy.orm import Session

from chat2rag.database.connection import SessionLocal
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

    @contextmanager
    def get_db_session(self) -> Generator[Session, None, None]:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def _fetch_all_tool(self) -> List[Tool]:
        """
        Fetch all tools from database
        """

        all_tools = []

        with self.get_db_session() as db:
            # Build basic queries
            base_query = db.query(CustomTool).filter(
                CustomTool.status == Status.ENABLED
            )
            # Obtain different types of tools respectively
            api_tools = base_query.filter(CustomTool.type == ToolType.API).all()
            mcp_tools = base_query.filter(CustomTool.type != ToolType.API).all()

            # Processing API tools
            for api_tool in api_tools:
                fetched_tools = api_tool._fetch_api_tools()
                all_tools.extend(fetched_tools.tools)

            # Processing MCP tools
            for mcp_tool in mcp_tools:
                try:
                    fetched_tools = mcp_tool._fetch_mcp_tools()
                    all_tools.extend(fetched_tools.tools)

                except Exception as e:
                    logger.warning("Get the tool %s failed: %s", mcp_tool.name, e)

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
