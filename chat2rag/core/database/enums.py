import enum


class Status(enum.Enum):
    ENABLED: int = 1
    DISABLED: int = 0


class ToolType(enum.Enum):
    API: str = "api"
    STDIO: str = "stdio"
    SSE: str = "sse"


class ToolMethod(enum.Enum):
    NONE: str = ""
    GET: str = "GET"
    POST: str = "POST"
