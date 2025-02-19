import os

from dotenv import load_dotenv

load_dotenv(override=True)


class Config:
    TITLE = "Chat2RAG(正式版)" if os.environ.get("DEPLOY_ENV") else "Chat2RAG(测试版)"
    BACKEND_HOST = os.environ.get("BACKEND_HOST")
    BACKEND_PORT = os.environ.get("BACKEND_PORT")
    # OPEN AI
    OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


CONFIG = Config()
