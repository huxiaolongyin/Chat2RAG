import os


class Config:
    TITLE = "Chat2RAG(正式版)" if os.environ.get("DEPLOY_ENV") else "Chat2RAG(测试版)"
    BACKEND_HOST = os.environ.get("BACKEND_HOST", "127.0.0.1")
    BACKEND_PORT = os.environ.get("BACKEND_PORT", "8000")
    # OPEN AI
    OPEN_BASE_URL = os.environ.get("OPEN_BASE_URL", "http://112.124.69.152:3001/v1")
    API_TOKEN = os.environ.get(
        "API_TOKEN", "sk-6YAYa64LCsy6G4wE91675dD6225845159bCa9f229d511e53"
    )


CONFIG = Config()
