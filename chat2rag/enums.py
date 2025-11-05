from enum import Enum


class DocumentType(str, Enum):
    """
    The type of document.

    QA Pair matches questions and answers for retrieval.
    QUESTION only matches questions and is generally used for precise answers.
    """

    QA_PAIR = "qa_pair"
    QUESTION = "question"


class ProcessType(str, Enum):
    BATCH = "batch"
    STREAM = "stream"


class Status(int, Enum):
    ENABLED: int = 1
    DISABLED: int = 0


class MCPToolType(str, Enum):
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
    CREATE_TIME = "create_time"
