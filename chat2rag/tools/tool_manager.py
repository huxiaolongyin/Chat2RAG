from contextlib import contextmanager
from typing import Generator, List

from haystack.tools import Toolset
from sqlalchemy.orm import Session

from chat2rag.core.database import CustomTool, SessionLocal
from chat2rag.core.database.enums import Status, ToolType
from chat2rag.logger import get_logger

logger = get_logger(__name__)


class ToolManager:
    """进行API、MCP的工具管理"""

    @contextmanager
    def get_db_session(self) -> Generator[Session, None, None]:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def fetch_tools(self, select_tools: List[str]) -> Toolset:
        """
        获取所有可用工具

        Args:
            select_tools: 选用的工具列表，["all"]表示获取所有工具，["tool1", "tool2"]表示获取指定的工具
        """
        if not select_tools:
            raise ValueError("没有指定任何工具")

        logger.debug("获取选择的工具: %s", select_tools)

        all_tools = None

        with self.get_db_session() as db:
            # 构建基础查询
            base_query = db.query(CustomTool).filter(
                CustomTool.status == Status.ENABLED
            )

            # 根据工具列表过滤
            if "all" in select_tools or "ALL" in select_tools:
                filter_tools = base_query
            else:
                filter_tools = base_query.filter(CustomTool.name.in_(select_tools))

            # 分别获取不同类型的工具
            api_tools = filter_tools.filter(CustomTool.type == ToolType.API).all()
            mcp_tools = filter_tools.filter(CustomTool.type != ToolType.API).all()

            # 处理API工具
            for api_tool in api_tools:
                fetched_tools = api_tool._fetch_api_tools()
                if all_tools is None:
                    all_tools = fetched_tools
                else:
                    all_tools += fetched_tools

            # 处理MCP工具
            for mcp_tool in mcp_tools:
                fetched_tools = mcp_tool._fetch_mcp_tools()
                if all_tools is None:
                    all_tools = fetched_tools
                else:
                    all_tools += fetched_tools

            if all_tools is None:
                raise ValueError("没有找到可用的工具")

            return all_tools


tool_manager = ToolManager()

if __name__ == "__main__":
    print(tool_manager.fetch_tools(["all"]))
