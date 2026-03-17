from enum import Enum


class DocumentType(str, Enum):
    """文档类型"""

    QUESTION = "question"
    QA_PAIR = "qa_pair"  # 问答对
    PDF = "pdf"
    WORD = "word"
    MARKDOWN = "markdown"
    TEXT = "text"
    WEB = "web"
    EXCEL = "excel"
    CSV = "csv"
    TSV = "tsv"


class ProcessType(str, Enum):
    BATCH = "batch"
    STREAM = "stream"


class Status(int, Enum):
    ENABLED: int = 1
    DISABLED: int = 0


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class CollectionSortField(str, Enum):
    COLLECTION_NAME = "collection_name"
    DOCUMENT_COUNT = "document_count"


class DocumentSortField(str, Enum):
    DOCUMENT_CONTENT = "content"


# ==================== Tool Enums ====================
class MCPToolType(str, Enum):
    STDIO: str = "stdio"
    SSE: str = "sse"
    STREAMABLE: str = "streamable"


class ToolMethod(str, Enum):
    NONE: str = ""
    GET: str = "GET"
    POST: str = "POST"


class ToolSortField(str, Enum):
    TOOL_NAME = "name"
    TOOL_DESC = "description"
    CREATE_TIME = "create_time"


class ToolType(str, Enum):
    API = "api"
    MCP = "mcp"
    ALL = "all"


class FileType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    XLS = "xls"
    CSV = "csv"
    TSV = "tsv"
    JSON = "json"
    UNKNOWN = "unknown"


class FileStatus(str, Enum):
    PENDING = "pending"
    PARSING = "parsing"
    PARSED = "parsed"
    FAILED = "failed"
