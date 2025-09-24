import os
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

promt_path = Path(__file__).parent / "prompt"


def load_str_env(name: str, required: bool = False) -> str:
    """
    Load environment variable as string
    :param name: name of the environment variable
    :param required: whether the environment variable is required
    """
    if os.environ.get(name):
        return os.environ.get(name)

    if required:
        raise Exception(f"Env {name} is not set")


def load_int_env(name: str, required: bool = False) -> int:
    """
    Load environment variable as int
    :param name: name of the environment variable
    :param required: whether the environment variable is required
    """
    if os.environ.get(name):
        return int(os.environ.get(name))

    if required:
        raise Exception(f"Env {name} is not set")


def load_list_env(name: str, required: bool = False) -> list:
    """ """
    if os.environ.get(name):
        return os.environ.get(name).split(",")

    if required:
        raise Exception(f"Env {name} is not set")


def load_float_env(name: str, required: bool = False) -> float:
    """
    Load environment variable as float
    :param name: name of the environment variable
    :param required: whether the environment variable is required
    """
    if os.environ.get(name):
        return float(os.environ.get(name))
    if required:
        raise Exception(f"Env {name} is not set")


def load_bool_env(name: str, required: bool = False) -> bool:
    """
    Load environment variable as bool
    :param name: name of the environment variable
    :param required: whether the environment variable is required
    """
    if os.environ.get(name):
        return os.environ.get(name).lower() in ["true", "1", "yes"]
    if required:
        raise Exception(f"Env {name} is not set")


def load_prompt(file_name: str, required: bool = False) -> str:
    """
    Load prompt from file
    :param file_name: name of the prompt file, file type is .txt
    :param required: whether the prompt file is required
    """
    file_path = promt_path / file_name
    if file_path.exists():
        result = file_path.read_text(encoding="utf-8")
        if not result and required:
            raise Exception(f"Prompt file {file_name} is empty")

        return result
    else:
        if required:
            raise Exception(f"Prompt file {file_name} is not found")
        return ""


class Config:
    """Backend configuration"""

    try:
        VERSION = version("chat2rag")
    except PackageNotFoundError:
        # 包未安装，可能处于开发模式
        VERSION = "unknown"

    # Project Catalogue
    ROOT_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = ROOT_DIR / "data"
    SQLITE_DIR = DATA_DIR / "sqlite"

    # Open AI LLM
    OPENAI_BASE_URL = load_str_env("OPENAI_BASE_URL", required=True)
    OPENAI_API_KEY = load_str_env("OPENAI_API_KEY", required=True)
    MODEL = load_str_env("MODEL") or "Qwen/Qwen2.5-72B-Instruct"
    DEFAULT_MODEL = MODEL  # 兼容旧版

    GENERATION_KWARGS = {
        "temperature": 0.15,
        "presence_penalty": -0.5,  # 改为0以平衡重复与多样性
        "frequency_penalty": -0.5,  # 添加轻微频率惩罚以减少重复
        "top_p": 0.95,  # 添加top_p参数限制token选择范围
        "seed": 1234,
        "extra_body": {"enable_thinking": False, "thinking_budget": 100},
    }

    # PROMPT_NAME
    PROMPT_NAME = load_str_env("PROMPT_NAME") or "默认"

    # Embedding Service
    EMBEDDING_OPENAI_URL = load_str_env("EMBEDDING_OPENAI_URL")
    EMBEDDING_MODEL = load_str_env("EMBEDDING_MODEL") or "360Zhinao-search"
    EMBEDDING_DIMENSIONS = load_int_env("EMBEDDING_DIMENSIONS") or 1024

    # Vector Store
    QDRANT_HOST = load_str_env("QDRANT_HOST") or "localhost"
    QDRANT_PORT = load_int_env("QDRANT_PORT") or 6333
    QDRANT_GRPC_PORT = load_int_env("QDRANT_GRPC_PORT") or 6334

    # Database
    POSTGRESQL_HOST = load_str_env("POSTGRESQL_HOST") or "localhost"
    POSTGRESQL_DATABASE = load_str_env("POSTGRESQL_DATABASE") or "chat2rag"
    POSTGRESQL_PASSWORD = load_str_env("POSTGRESQL_PASSWORD") or "123456"
    DATABASE_URL = f"postgresql://postgres:{POSTGRESQL_PASSWORD}@{POSTGRESQL_HOST}:5432/{POSTGRESQL_DATABASE}"

    # RAG
    RAG_PROMPT_TEMPLATE = load_prompt("rag_default_prompt.txt")

    # Document Retriever
    TOP_K = load_int_env("TOP_K") or 5
    SCORE_THRESHOLD = load_float_env("SCORE_THRESHOLD") or 0.65
    PRECISION_MODE = load_bool_env("PRECISION_MODE") or 0

    # The threshold for precise retrieval
    PRECISION_THRESHOLD = load_float_env("PRECISION_THRESHOLD") or 0.88

    # Function
    FUNCTION_PROMPT_TEMPLATE = load_prompt("function_prompt.txt")
    FUNCION_ENABLED = load_bool_env("FUNCION_ENABLED") or False
    # GAODE_API_KEY = load_str_env("GAODE_API_KEY", required=True)

    # API RETURN FORM
    BATCH_OR_STREAM = load_str_env("BATCH_OR_STREAM") or "batch"

    # Chat session management
    CHAT_ROUNDS = load_int_env("CHAT_ROUNDS") or 5
    MODALITIES = load_list_env("MODALITIES") or ["text"]
    TOOLS = load_list_env("TOOLS") or []

    # WEB
    WEB_ROUTE_PREFIX = load_str_env("WEB_ROUTE_PREFIX") or "/api"
    BACKEND_PORT = load_int_env("BACKEND_PORT") or 8000

    # TELEMETRY
    TELEMETRY_ENABLED = load_bool_env("TELEMETRY_ENABLED")

    # MODEL
    MODEL_LIST = [
        # {"name": "Qwen-Plus", "id": "qwen-plus"},
        {"name": "Deepseek-v3", "id": "Pro/deepseek-ai/DeepSeek-V3"},
        {"name": "Qwen2.5-14B", "id": "Qwen/Qwen2.5-14B-Instruct"},
        {"name": "Qwen2.5-32B", "id": "Qwen/Qwen2.5-32B-Instruct"},
        {"name": "Qwen2.5-72B", "id": "Qwen/Qwen2.5-72B-Instruct"},
        {"name": "Qwen3-32B", "id": "Qwen/Qwen3-32B"},
        {"name": "Qwen3-14B", "id": "Qwen/Qwen3-14B"},
    ]

    # old_version
    GAODE_API_KEY = load_str_env("GAODE_API_KEY")


CONFIG = Config()
