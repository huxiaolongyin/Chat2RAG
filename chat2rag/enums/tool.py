from enum import Enum


class ToolType(str, Enum):
    API: str = "api"
    STDIO: str = "stdio"
    SSE: str = "sse"
    STREAMABLE: str = "streamable"


class ToolMethod(str, Enum):
    NONE: str = ""
    GET: str = "GET"
    POST: str = "POST"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class ToolSortField(str, Enum):
    TOOL_NAME = "name"
    TOOL_DESC = "description"
