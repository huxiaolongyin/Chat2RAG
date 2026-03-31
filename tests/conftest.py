# import asyncio
import os

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from tortoise import Tortoise

# 设置测试的环境变量
os.environ["PYTEST_CURRENT_TEST"] = "True"
os.environ["QDRANT_LOCATION"] = ":memory:"
os.environ["EMBEDDING_OPENAI_URL"] = "https://api.siliconflow.cn/v1"
os.environ["EMBEDDING_MODEL"] = "Qwen/Qwen3-Embedding-0.6B"
os.environ["EMBEDDING_API_KEY"] = "sk-xanhyopslamqkebregfhldoudjkjyunlhebkrcslwlbbsuyu"
os.environ["EMBEDDING_DIMENSIONS"] = "1024"
os.environ["SERPERDEV_API_KEY"] = "st-123"


from chat2rag.utils.qdrant_store import get_client

# @pytest.fixture(scope="session")
# def event_loop():
#     """Create event loop for test session."""
#     loop = asyncio.get_event_loop_policy().new_event_loop()
#     yield loop
#     loop.close()


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


@pytest.fixture(scope="function", autouse=True)
async def initialize_qdrant():
    """Initialize and clean up Qdrant for each test function."""
    client = get_client()

    # 清理所有existing collections
    collections = await client.get_collections()

    for collection in collections.collections:
        await client.delete_collection(collection.name)

    yield

    # 测试后清理
    collections = await client.get_collections()
    for collection in collections.collections:
        await client.delete_collection(collection.name)

    await client.close()
    get_client.cache_clear()


@pytest.fixture
async def client():
    """Create test client."""
    from chat2rag.api.routes import router
    from chat2rag.config import CONFIG
    from chat2rag.middleware import ExceptionHandlerMiddleware, LoggingMiddleware

    # 创建不带 lifespan 的测试 app
    app = FastAPI(title="Chat2RAG Test")

    # 注意顺序：异常处理在外层，日志记录在内层
    app.add_middleware(ExceptionHandlerMiddleware)
    app.add_middleware(LoggingMiddleware, log_level="info", log_body=True)

    app.include_router(router, prefix=CONFIG.WEB_ROUTE_PREFIX)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
