from enum import Enum


class ToolType(Enum):
    API: str = "api"
    STDIO: str = "stdio"
    SSE: str = "sse"
    STREAMABLE: str = "streamable"


class ToolMethod(Enum):
    NONE: str = ""
    GET: str = "GET"
    POST: str = "POST"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class ToolSortField(str, Enum):
    TOOL_NAME = "name"
    TOOL_DESC = "description"
