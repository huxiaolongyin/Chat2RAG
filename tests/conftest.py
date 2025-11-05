import asyncio

import pytest
from httpx import ASGITransport, AsyncClient
from tortoise import Tortoise

from chat2rag.config import CONFIG

# from tortoise.contrib.fastapi import RegisterTortoise


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function", autouse=True)
async def initialize_db():
    """Initialize test database for each test function."""
    # 初始化 Tortoise ORM
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={
            "app_system": [
                "chat2rag.models",  # 确保这里包含了所有模型
            ]
        },
    )
    # 创建表结构
    await Tortoise.generate_schemas()

    yield

    # 清理
    await Tortoise.close_connections()


@pytest.fixture
async def client():
    """Create test client."""
    from fastapi import FastAPI

    from chat2rag.api.routes import router

    # 创建不带 lifespan 的测试 app
    app = FastAPI(title="Chat2RAG Test")
    app.include_router(router, prefix=CONFIG.WEB_ROUTE_PREFIX)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
