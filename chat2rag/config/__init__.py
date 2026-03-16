import os
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from dotenv import load_dotenv

if not os.environ.get("PYTEST_CURRENT_TEST"):
    load_dotenv(override=True)

PROMPT_PATH = Path(__file__).parent.parent / "prompt"

_load_str_env = lambda name: os.environ.get(name)
_load_int_env = lambda name: int(os.environ.get(name)) if os.environ.get(name) else None
_load_list_env = (
    lambda name: os.environ.get(name).split(",") if os.environ.get(name) else None
)
_load_float_env = (
    lambda name: float(os.environ.get(name)) if os.environ.get(name) else None
)
_load_bool_env = (
    lambda name: os.environ.get(name).lower() in ["true", "1", "yes"]
    if os.environ.get(name)
    else None
)


def load_prompt(file_name: str, required: bool = False) -> str:
    file_path = PROMPT_PATH / file_name
    if file_path.exists():
        result = file_path.read_text(encoding="utf-8")
        if not result and required:
            raise Exception(f"Prompt file {file_name} is empty")
        return result
    else:
        if required:
            raise Exception(f"Prompt file {file_name} is not found")
        return ""


from chat2rag.config.database import DATABASE_URL, TORTOISE_ORM
from chat2rag.config.model import (
    CHAT_V1_DEFAULT_MODELS,
    DEFAULT_MODEL,
    GENERATION_KWARGS,
    MODEL,
    MODEL_LIST,
    PROCESS_MODEL,
)
from chat2rag.config.prompts import FUNCTION_PROMPT_TEMPLATE, RAG_PROMPT_TEMPLATE
from chat2rag.config.rag import (
    EMBEDDING_API_KEY,
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    EMBEDDING_OPENAI_URL,
    PRECISION_MODE,
    PRECISION_THRESHOLD,
    QDRANT_LOCATION,
    RETRIEVAL_MODE,
    SCORE_THRESHOLD,
    SPARSE_MODEL_PATH,
    TOP_K,
)


class Config:
    try:
        VERSION = version("chat2rag")
    except PackageNotFoundError:
        VERSION = "unknown"

    ROOT_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = ROOT_DIR / "data"
    SQLITE_DIR = DATA_DIR / "sqlite"

    PROMPT_NAME = _load_str_env("PROMPT_NAME") or "默认"

    FUNCTION_ENABLED = _load_bool_env("FUNCTION_ENABLED") or False

    BATCH_OR_STREAM = _load_str_env("BATCH_OR_STREAM") or "batch"

    CHAT_ROUNDS = _load_int_env("CHAT_ROUNDS") or 5
    MODALITIES = _load_list_env("MODALITIES") or ["text"]
    TOOLS = _load_list_env("TOOLS") or []

    WEB_ROUTE_PREFIX = _load_str_env("WEB_ROUTE_PREFIX") or "/api"
    BACKEND_PORT = _load_int_env("BACKEND_PORT") or 8000

    TELEMETRY_ENABLED = _load_bool_env("TELEMETRY_ENABLED") or False

    IS_FLOW = _load_bool_env("IS_FLOW") or False

    # 命令匹配配置
    COMMAND_LLM_FALLBACK = _load_bool_env("COMMAND_LLM_FALLBACK") or True
    COMMAND_FUZZY_THRESHOLD = _load_float_env("COMMAND_FUZZY_THRESHOLD") or 0.7

    DATABASE_URL = DATABASE_URL
    TORTOISE_ORM = TORTOISE_ORM

    MODEL = MODEL
    PROCESS_MODEL = PROCESS_MODEL
    DEFAULT_MODEL = DEFAULT_MODEL
    MODEL_LIST = MODEL_LIST
    CHAT_V1_DEFAULT_MODELS = CHAT_V1_DEFAULT_MODELS
    GENERATION_KWARGS = GENERATION_KWARGS

    EMBEDDING_OPENAI_URL = EMBEDDING_OPENAI_URL
    EMBEDDING_MODEL = EMBEDDING_MODEL
    EMBEDDING_DIMENSIONS = EMBEDDING_DIMENSIONS
    EMBEDDING_API_KEY = EMBEDDING_API_KEY
    QDRANT_LOCATION = QDRANT_LOCATION
    TOP_K = TOP_K
    SCORE_THRESHOLD = SCORE_THRESHOLD
    PRECISION_MODE = PRECISION_MODE
    PRECISION_THRESHOLD = PRECISION_THRESHOLD
    RETRIEVAL_MODE = RETRIEVAL_MODE
    SPARSE_MODEL_PATH = SPARSE_MODEL_PATH

    RAG_PROMPT_TEMPLATE = RAG_PROMPT_TEMPLATE
    FUNCTION_PROMPT_TEMPLATE = FUNCTION_PROMPT_TEMPLATE


CONFIG = Config()
tortoise_orm = TORTOISE_ORM

__all__ = [
    "CONFIG",
    "tortoise_orm",
    "load_prompt",
    "_load_str_env",
    "_load_int_env",
    "_load_list_env",
    "_load_float_env",
    "_load_bool_env",
]
