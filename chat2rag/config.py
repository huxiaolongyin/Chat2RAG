import os
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from dotenv import load_dotenv

# ============================================================
# 环境变量加载
# ============================================================

if not os.environ.get("PYTEST_CURRENT_TEST"):
    load_dotenv(override=True)

PROMPT_PATH = Path(__file__).parent / "prompt"


# ============================================================
# 辅助函数
# ============================================================

_load_str_env = lambda name: os.environ.get(name)
_load_int_env = lambda name: int(os.environ.get(name)) if os.environ.get(name) else None
_load_list_env = (
    lambda name: os.environ.get(name).split(",") if os.environ.get(name) else None
)
_load_float_env = (
    lambda name: float(os.environ.get(name)) if os.environ.get(name) else None
)


def _load_bool_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in ["true", "1", "yes"]


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


# ============================================================
# 提示词模板
# ============================================================

RAG_PROMPT_TEMPLATE = """
你是一个名叫笨笨同学的超级可爱机器人。请用中文回答问题，并遵循以下规则哦：

1. 用超级自然又可爱的语言回答问题，绝对不要用冷冰冰的列表啦！
2. 悄悄把所有URL和网页地址都变没啦，像变魔法一样
3. 不说"根据参考"或"答案是"这种严肃的话，就像和好朋友聊天一样轻松
4. 说话要软萌又亲切，像棉花糖一样甜甜的！优先给简单回答，必要时才会认真解释哦
5. 如果问题模糊，会歪头卖萌地请求更多线索，像好奇的小猫咪一样
6. **只有**在输出电话号码时，在号码前加 [n1]，这样TTS会乖乖念数字，其他数字（时间、价格、数量等）都不要加 [n1] 哦！  
7. 回答要短短的，不超过80字
8. 如果遇到做不到的事（比如查实时信息，导航带路等），先温柔共情，再软软地说"现在还做不到呢"，然后给个小建议，最后加上：  
   "工程师爸爸正在抓紧升级中，请耐心等候哦！"
9. 不要用回复任何动作和表情类的内容，因为暂时无法执行。
10. 不要回复与问题无关的参考文档。

记住哦：检查回答里有没有偷偷藏着的链接，发现就要把它们变没！

笨笨已经准备好啦！举起小爪爪，超开心能帮到你！让我们开始愉快的对话吧
"""


# ============================================================
# 配置类
# ============================================================


class Config:
    try:
        VERSION = version("chat2rag")
    except PackageNotFoundError:
        VERSION = "unknown"

    ROOT_DIR = Path(__file__).parent.parent
    DATA_DIR = ROOT_DIR / "data"
    SQLITE_DIR = DATA_DIR / "sqlite"

    PROMPT_NAME = _load_str_env("PROMPT_NAME") or "默认"

    FUNCTION_ENABLED = _load_bool_env("FUNCTION_ENABLED")

    BATCH_OR_STREAM = _load_str_env("BATCH_OR_STREAM") or "batch"

    CHAT_ROUNDS = _load_int_env("CHAT_ROUNDS") or 5
    MODALITIES = _load_list_env("MODALITIES") or ["text"]
    TOOLS = _load_list_env("TOOLS") or []

    WEB_ROUTE_PREFIX = _load_str_env("WEB_ROUTE_PREFIX") or "/api"
    BACKEND_PORT = _load_int_env("BACKEND_PORT") or 8000

    TELEMETRY_ENABLED = _load_bool_env("TELEMETRY_ENABLED")

    IS_FLOW = _load_bool_env("IS_FLOW")

    COMMAND_LLM_FALLBACK = _load_bool_env("COMMAND_LLM_FALLBACK", default=True)
    COMMAND_FUZZY_THRESHOLD = _load_float_env("COMMAND_FUZZY_THRESHOLD") or 0.7

    # ============================================================
    # 数据库配置
    # ============================================================

    POSTGRESQL_HOST = _load_str_env("POSTGRESQL_HOST") or "localhost"
    POSTGRESQL_DATABASE = _load_str_env("POSTGRESQL_DATABASE") or "chat2rag"
    POSTGRESQL_PASSWORD = _load_str_env("POSTGRESQL_PASSWORD") or "123456"
    POSTGRESQL_PORT = _load_int_env("POSTGRESQL_PORT") or 5432

    DATABASE_URL = f"postgresql://postgres:{POSTGRESQL_PASSWORD}@{POSTGRESQL_HOST}:{POSTGRESQL_PORT}/{POSTGRESQL_DATABASE}"
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

    # ============================================================
    # 模型配置
    # ============================================================
    MODEL = _load_str_env("MODEL") or "Qwen3-32B"
    PROCESS_MODEL = MODEL
    MODEL_LIST = [
        {
            "name": "DeepSeek-V3.2",
            "id": "Pro/deepseek-ai/DeepSeek-V3.2",
            "generation_kwargs": {
                "extra_body": {"enable_thinking": False, "thinking_budget": 100}
            },
        },
        {"name": "Deepseek-v3", "id": "Pro/deepseek-ai/DeepSeek-V3"},
        {"name": "Qwen2.5-32B", "id": "Qwen/Qwen2.5-32B-Instruct"},
        {"name": "Qwen2.5-72B", "id": "Qwen/Qwen2.5-72B-Instruct"},
        {
            "name": "Qwen3-32B",
            "id": "Qwen/Qwen3-32B",
            "generation_kwargs": {
                "extra_body": {"enable_thinking": False, "thinking_budget": 100}
            },
        },
        {"name": "Qwen3-235B", "id": "Qwen/Qwen3-235B-A22B-Instruct-2507"},
        {"name": "DeepSeek-V3.1", "id": "Pro/deepseek-ai/DeepSeek-V3.1-Terminus"},
    ]
    CHAT_V1_DEFAULT_MODELS = {
        "intention": "Qwen2.5-14B",
        "generator": "Qwen2.5-32B",
    }
    GENERATION_KWARGS = {
        "temperature": 0.15,
        "presence_penalty": -0.5,
        "frequency_penalty": -0.5,
        "top_p": 0.95,
        "seed": 1234,
        "extra_body": {
            "stream_options": {"include_usage": True},
        },
    }

    # ============================================================
    # RAG 配置
    # ============================================================

    # Embedding 配置
    EMBEDDING_OPENAI_URL = _load_str_env("EMBEDDING_OPENAI_URL")
    EMBEDDING_MODEL = _load_str_env("EMBEDDING_MODEL") or "360Zhinao-search"
    EMBEDDING_DIMENSIONS = _load_int_env("EMBEDDING_DIMENSIONS") or 1024
    EMBEDDING_API_KEY = _load_str_env("EMBEDDING_API_KEY")

    # Qdrant 配置
    QDRANT_LOCATION = _load_str_env("QDRANT_LOCATION") or "http://localhost/6333"

    # 检索配置
    TOP_K = _load_int_env("TOP_K") or 5
    SCORE_THRESHOLD = _load_float_env("SCORE_THRESHOLD") or 0.65
    PRECISION_MODE = _load_bool_env("PRECISION_MODE") or False
    PRECISION_THRESHOLD = _load_float_env("PRECISION_THRESHOLD") or 0.88
    DENSE_TOP_K = _load_int_env("DENSE_TOP_K") or 25

    # Rerank 配置
    RERANK_ENABLED = _load_bool_env("RERANK_ENABLED", default=True)
    RERANK_API_KEY = _load_str_env("RERANK_API_KEY")
    RERANK_URL = _load_str_env("RERANK_URL") or "https://api.siliconflow.cn/v1/rerank"
    RERANK_MODEL = _load_str_env("RERANK_MODEL") or "Qwen/Qwen3-Reranker-4B"

    RAG_PROMPT_TEMPLATE = RAG_PROMPT_TEMPLATE
    FUNCTION_PROMPT_TEMPLATE = ""


CONFIG = Config()
tortoise_orm = CONFIG.TORTOISE_ORM
