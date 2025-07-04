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
