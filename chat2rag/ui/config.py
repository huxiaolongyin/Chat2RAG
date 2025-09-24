import os

from dotenv import load_dotenv

load_dotenv(override=True)


class Config:
    TITLE = "Chat2RAG(正式版)" if os.environ.get("DEPLOY_ENV") else "Chat2RAG(测试版)"


CONFIG = Config()
