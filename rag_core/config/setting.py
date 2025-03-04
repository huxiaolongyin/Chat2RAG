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

    # 项目目录
    ROOT_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = ROOT_DIR / "data"
    SQLITE_DIR = DATA_DIR / "sqlite"

    # Open AI LLM
    ONE_API_HOST = load_str_env("ONE_API_HOST") or "localhost"
    ONE_API_PORT = load_int_env("ONE_API_PORT") or 3001
    OPENAI_BASE_URL = f"http://{ONE_API_HOST}:{ONE_API_PORT}/v1"
    OPENAI_API_KEY = load_str_env("OPENAI_API_KEY", required=True)
    DEFAULT_INTENTION_MODEL = load_str_env("DEFAULT_INTENTION_MODEL") or "Qwen2.5-14B"
    DEFAULT_GENERATOR_MODEL = load_str_env("DEFAULT_GENERATOR_MODEL") or "Qwen2.5-32B"

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

    # Retriever
    TOP_K = load_int_env("TOP_K") or 5
    SCORE_THRESHOLD = load_float_env("SCORE_THRESHOLD") or 0.65
    # 精准检索的阈值
    PRECISION_THRESHOLD = load_float_env("PRECISION_THRESHOLD") or 0.88

    # Function
    FUNCTION_PROMPT_TEMPLATE = load_prompt("function_prompt.txt")
    FUNCION_ENABLED = load_bool_env("FUNCION_ENABLED") or False
    GAODE_API_KEY = load_str_env("GAODE_API_KEY", required=True)

    # WEB
    WEB_ROUTE_PREFIX = load_str_env("WEB_ROUTE_PREFIX") or "/api/v1"
    BACKEND_PORT = load_int_env("BACKEND_PORT") or 8000

    # TELEMETRY
    TELEMETRY_ENABLED = load_bool_env("TELEMETRY_ENABLED")


CONFIG = Config()
