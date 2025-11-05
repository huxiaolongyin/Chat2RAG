from tortoise import Tortoise
from config import SETTINGS
from contextlib import asynccontextmanager
import functools


@asynccontextmanager
async def db_context():
    """数据库连接上下文管理器"""
    await Tortoise.init(config=SETTINGS.TORTOISE_ORM)
    try:
        yield
    finally:
        await Tortoise.close_connections()


def with_db(func):
    """数据库连接装饰器"""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        async with db_context():
            return await func(*args, **kwargs)

    return wrapper
