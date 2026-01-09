from typing import Any, Dict

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):

    # 数据库配置
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "123456"
    DB_NAME: str = "htw_mcp"

    # Aerich 配置
    MIGRATION_LOCATION: str = "chat2rag/mcp/migrations"

    # Tortoise ORM配置
    @property
    def TORTOISE_ORM(self) -> Dict[str, Any]:
        return {
            "connections": {
                "default": {
                    "engine": "tortoise.backends.asyncpg",
                    "credentials": {
                        "host": self.DB_HOST,
                        "port": self.DB_PORT,
                        "user": self.DB_USER,
                        "password": self.DB_PASSWORD,
                        "database": self.DB_NAME,
                        "minsize": 1,
                        "maxsize": 100,
                    },
                },
            },
            "apps": {
                "app_system": {
                    "models": [
                        "aerich.models",
                        "chat2rag.mcp.models.scene",
                        "chat2rag.mcp.models.entity",
                        "chat2rag.mcp.models.device",
                        "chat2rag.mcp.models.item",
                        "chat2rag.mcp.models.cart",
                    ],
                    "default_connection": "default",
                },
            },
            "use_tz": False,
            "timezone": "Asia/Shanghai",
        }


SETTINGS = Settings()
