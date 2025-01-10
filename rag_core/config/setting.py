import os

# from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version

from dotenv import load_dotenv
from haystack.utils import Secret

from .embedding_check import EmbeddingUrlMonitor

load_dotenv(override=True)


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


class Config:
    """Backend configuration"""

    try:
        VERSION = version("chat2rag")
    except PackageNotFoundError:
        # 包未安装，可能处于开发模式
        VERSION = "unknown"

    # 项目目录
    # ROOT_DIR = Path(__file__).parent.parent.parent
    # LOG_DIR = ROOT_DIR / "logs"

    # OPENAI
    OPENAI_API_KEY = Secret.from_env_var("OPENAI_API_KEY")
    OPENAI_BASE_URL = load_str_env("OPENAI_BASE_URL", required=True)
    DEFAULT_TEMPLATE = """
    你是一个先进的人工智能助手，名字叫 笨笨同学，你的目标是帮助用户并提供有用、安全和诚实的回答。请遵循以下准则：
    1. 现在提供一些查询内容，使用中文直接回答问题。
    2. 如果查询内容与问题不相关，请直接根据问题回答。
    3. 提供准确和最新的信息。如果不确定，请说明你不确定。
    4. 尽可能给出清晰、简洁的回答，但在需要时也要提供详细解释。
    5. 请使用人性化的语言。
    6. 不必说"根据参考内容"，也不必说"答案是"，请直接回复答案。
    7. 请不要使用列表的形式回答。
    8. 回复内容请尽量在200字以内。
    你已准备好协助用户解决各种问题和任务。请以友好和乐于助人的态度开始对话。
    """

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
    embedding_monitor = EmbeddingUrlMonitor.get_instance()
    embedding_monitor.setup(
        local_url=LOCAL_EMBEDDING_OPENAI_URL, remote_url=REMOTE_EMBEDDING_OPENAI_URL
    )

    EMBEDDING_OPENAI_URL = embedding_monitor.get_current_url()

    # MODEL
    TOP_K = load_int_env("TOP_K", required=False) or 5
    SCORE_THRESHOLD = load_float_env("SCORE_THRESHOLD", required=False) or 0.7

    # WEB
    WEB_ROUTE_PREFIX = load_str_env("WEB_ROUTE_PREFIX", required=False) or "/api/v1"
    WEB_PORT = load_int_env("WEB_PORT", required=False) or 8000

    # OTHER SERVICE
    GAODE_API_KEY = load_str_env("GAODE_API_KEY", required=True)

    # TELEMETRY
    TELEMETRY_ENABLED = load_bool_env("TELEMETRY_ENABLED", required=False)


CONFIG = Config()
