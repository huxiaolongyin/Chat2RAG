import os

# from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from dotenv import load_dotenv
from haystack.utils import Secret

# from .embedding_check import EmbeddingUrlMonitor

load_dotenv(override=True)

promt_path = Path(__file__).parent / "prompt"
# @lru_cache(maxsize=1)
# def get_embedding_monitor(local_url, remote_url):
#     return EmbeddingUrlMonitor(local_url=local_url, remote_url=remote_url)


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
    # LOG_DIR = ROOT_DIR / "logs"

    # OPENAI
    OPENAI_API_KEY = Secret.from_env_var("OPENAI_API_KEY")
    OPENAI_BASE_URL = load_str_env("OPENAI_BASE_URL", required=True)

    RAG_PROMPT_TEMPLATE = load_prompt("rag_default_prompt.txt")

    # Function
    FUNCTION_PROMPT_TEMPLATE = load_prompt("function_prompt.txt")
    FUNCION_ENABLED = load_bool_env("FUNCION_ENABLED", required=False) or False

    # EMBEDDING
    QDRANT_HOST = load_str_env("QDRANT_HOST", required=False) or "localhost"
    QDRANT_PORT = load_int_env("QDRANT_PORT", required=False) or 6333
    QDRANT_GRPC_PORT = load_int_env("QDRANT_GRPC_PORT", required=False) or 6334
    LOCAL_EMBEDDING_OPENAI_URL = load_str_env(
        "LOCAL_EMBEDDING_OPENAI_URL", required=False
    )
    REMOTE_EMBEDDING_OPENAI_URL = load_str_env(
        "REMOTE_EMBEDDING_OPENAI_URL", required=False
    )
    # embedding_monitor = EmbeddingUrlMonitor.get_instance()
    # embedding_monitor.setup(
    #     local_url=LOCAL_EMBEDDING_OPENAI_URL, remote_url=REMOTE_EMBEDDING_OPENAI_URL
    # )

    # EMBEDDING_OPENAI_URL = embedding_monitor.get_current_url()
    EMBEDDING_OPENAI_URL = REMOTE_EMBEDDING_OPENAI_URL
    # MODEL CONFIG
    TOP_K = load_int_env("TOP_K", required=False) or 5
    SCORE_THRESHOLD = load_float_env("SCORE_THRESHOLD", required=False) or 0.7

    # DATABASE
    # 确保目录存在
    SQLITE_DIR.mkdir(parents=True, exist_ok=True)

    DATABASE_URL = (
        load_str_env("POSTGRESQL_DATABASE_URL", required=False)
        or f"sqlite:///{SQLITE_DIR}/chat2rag.db"
    )

    # WEB
    WEB_ROUTE_PREFIX = load_str_env("WEB_ROUTE_PREFIX", required=False) or "/api/v1"
    WEB_PORT = load_int_env("WEB_PORT", required=False) or 8000

    # OTHER SERVICE
    GAODE_API_KEY = load_str_env("GAODE_API_KEY", required=True)

    # TELEMETRY
    TELEMETRY_ENABLED = load_bool_env("TELEMETRY_ENABLED", required=False)


CONFIG = Config()
