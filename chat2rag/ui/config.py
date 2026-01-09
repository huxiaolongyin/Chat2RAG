import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv(override=True)


@dataclass
class CONFIG:
    TITLE: str = "Chat2RAG(正式版)" if os.environ.get("DEPLOY_ENV") else "Chat2RAG(测试版)"

    # API配置
    BASE_URL: str = os.getenv("BASE_URL", "http://127.0.0.1:8000")
    REQUEST_TIMEOUT: int = 30

    # 消息管理
    MAX_MESSAGE_HISTORY: int = 100
    DEFAULT_CHAT_ROUNDS: int = 5

    # UI配置
    SCORE_DISPLAY_PRECISION: int = 2
    SPINNER_TEXT: str = "生成回答中"

    # 缓存
    CACHE_TTL: int = 300  # 5分钟缓存
