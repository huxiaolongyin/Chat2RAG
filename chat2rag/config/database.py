import os

_load_str_env = lambda name: os.environ.get(name)
_load_int_env = lambda name: int(os.environ.get(name)) if os.environ.get(name) else None

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
