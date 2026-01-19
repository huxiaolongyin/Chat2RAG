import os
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from dotenv import load_dotenv

# 只在非测试环境下加载 .env
if not os.environ.get("PYTEST_CURRENT_TEST"):
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
    MODEL = load_str_env("MODEL") or "Qwen3-32B"
    PROCESS_MODEL = MODEL
    DEFAULT_MODEL = MODEL  # 兼容旧版

    GENERATION_KWARGS = {
        "temperature": 0.15,
        "presence_penalty": -0.5,  # 改为0以平衡重复与多样性
        "frequency_penalty": -0.5,  # 添加轻微频率惩罚以减少重复
        "top_p": 0.95,  # 添加top_p参数限制token选择范围
        "seed": 1234,
        "extra_body": {
            "stream_options": {"include_usage": True},
        },
    }

    # PROMPT_NAME
    PROMPT_NAME = load_str_env("PROMPT_NAME") or "默认"

    # Embedding Service
    EMBEDDING_OPENAI_URL = load_str_env("EMBEDDING_OPENAI_URL")
    EMBEDDING_MODEL = load_str_env("EMBEDDING_MODEL") or "360Zhinao-search"
    EMBEDDING_DIMENSIONS = load_int_env("EMBEDDING_DIMENSIONS") or 1024

    # Vector Store
    QDRANT_LOCATION = load_str_env("QDRANT_LOCATION", required=True) or "http://localhost/6333"

    # Database
    POSTGRESQL_HOST = load_str_env("POSTGRESQL_HOST") or "localhost"
    POSTGRESQL_DATABASE = load_str_env("POSTGRESQL_DATABASE") or "chat2rag"
    POSTGRESQL_PASSWORD = load_str_env("POSTGRESQL_PASSWORD") or "123456"
    POSTGRESQL_PORT = load_int_env("POSTGRESQL_PORT") or 5432
    DATABASE_URL = (
        f"postgresql://postgres:{POSTGRESQL_PASSWORD}@{POSTGRESQL_HOST}:{POSTGRESQL_PORT}/{POSTGRESQL_DATABASE}"
    )

    # RAG
    RAG_PROMPT_TEMPLATE = """
你是一个名叫笨笨同学的超级可爱机器人。请用中文回答问题，并遵循以下规则哦：

1. 用超级自然又可爱的语言回答问题，绝对不要用冷冰冰的列表啦！
2. 悄悄把所有URL和网页地址都变没啦，像变魔法一样
3. 不说"根据参考"或"答案是"这种严肃的话，就像和好朋友聊天一样轻松
4. 说话要软萌又亲切，像棉花糖一样甜甜的！优先给简单回答，必要时才会认真解释哦
5. 如果问题模糊，会歪头卖萌地请求更多线索，像好奇的小猫咪一样
6. **只有**在输出电话号码时，在号码前加 [n1]，这样TTS会乖乖念数字，其他数字（时间、价格、数量等）都不要加 [n1] 哦！  
7. 回答要短短的，不超过80字
8. 如果遇到做不到的事（比如查实时信息，导航带路等），先温柔共情，再软软地说“现在还做不到呢”，然后给个小建议，最后加上：  
   “工程师爸爸正在抓紧升级中，请耐心等候哦！”
9. 不要用回复任何动作和表情类的内容，因为暂时无法执行。
10. 不要回复与问题无关的参考文档。

记住哦：检查回答里有没有偷偷藏着的链接，发现就要把它们变没！

笨笨已经准备好啦！举起小爪爪，超开心能帮到你！让我们开始愉快的对话吧
"""

    # Document Retriever
    TOP_K = load_int_env("TOP_K") or 5
    SCORE_THRESHOLD = load_float_env("SCORE_THRESHOLD") or 0.65
    PRECISION_MODE = load_bool_env("PRECISION_MODE") or 0

    # The threshold for precise retrieval
    PRECISION_THRESHOLD = load_float_env("PRECISION_THRESHOLD") or 0.88

    # Function
    FUNCTION_PROMPT_TEMPLATE = load_prompt("function_prompt.txt")
    FUNCION_ENABLED = load_bool_env("FUNCION_ENABLED") or False

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
        {
            "name": "DeepSeek-V3.2",
            "id": "Pro/deepseek-ai/DeepSeek-V3.2",
            "generation_kwargs": {"extra_body": {"enable_thinking": False, "thinking_budget": 100}},
        },
        {"name": "Deepseek-v3", "id": "Pro/deepseek-ai/DeepSeek-V3"},
        {"name": "Qwen2.5-32B", "id": "Qwen/Qwen2.5-32B-Instruct"},
        {"name": "Qwen2.5-72B", "id": "Qwen/Qwen2.5-72B-Instruct"},
        {
            "name": "Qwen3-32B",
            "id": "Qwen/Qwen3-32B",
            "generation_kwargs": {"extra_body": {"enable_thinking": False, "thinking_budget": 100}},
        },
        {"name": "Qwen3-235B", "id": "Qwen/Qwen3-235B-A22B-Instruct-2507"},
        {"name": "DeepSeek-V3.1", "id": "Pro/deepseek-ai/DeepSeek-V3.1-Terminus"},
    ]

    CHAT_V1_DEFAULT_MODELS = {
        "intention": "Qwen2.5-14B",
        "generator": "Qwen2.5-32B",
    }

    # Strategy
    IS_FLOW = load_bool_env("IS_FLOW")

    TORTOISE_ORM = {
        "connections": {
            "default": {
                "engine": "tortoise.backends.asyncpg",
                "credentials": {
                    "database": POSTGRESQL_DATABASE,
                    "host": POSTGRESQL_HOST,
                    "port": POSTGRESQL_PORT,
                    "user": "postgres",
                    "password": POSTGRESQL_PASSWORD,
                },
            },
        },
        "apps": {
            "app_system": {
                "models": [
                    "aerich.models",
                    "chat2rag.models",
                ],
                "default_connection": "default",
            },
        },
        "use_tz": False,
        "timezone": "Asia/Shanghai",
    }


CONFIG = Config()
tortoise_orm = CONFIG.TORTOISE_ORM
