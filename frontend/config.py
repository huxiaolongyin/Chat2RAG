import os


class Config:
    TITLE = "Chat2RAG(正式版)" if os.environ.get("DEPLOY_ENV") else "Chat2RAG(测试版)"
    BACKEND_HOST = os.environ.get("BACKEND_HOST", "127.0.0.1")
    BACKEND_PORT = os.environ.get("BACKEND_PORT", "8000")


CONFIG = Config()
