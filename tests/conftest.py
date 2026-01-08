import asyncio
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from tortoise import Tortoise

from chat2rag.config import CONFIG
from chat2rag.middleware import ExceptionHandlerMiddleware, LoggingMiddleware

# from tortoise.contrib.fastapi import RegisterTortoise


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def qdrant_client():
    """Create in-memory Qdrant client for testing."""
    # 使用临时目录作为存储路径，测试结束后自动清理
    with tempfile.TemporaryDirectory() as temp_dir:
        client = QdrantClient(path=temp_dir)

        # 创建测试用的集合（根据你的实际需求调整）
        test_collections = ["test_collection_1", "test_collection_2", "knowledge_base"]
        for collection_name in test_collections:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=1024, distance=Distance.COSINE),  # 根据你使用的embedding模型调整
            )

        yield client


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
    # 注意顺序：异常处理在外层，日志记录在内层
    app.add_middleware(ExceptionHandlerMiddleware)
    app.add_middleware(LoggingMiddleware, log_level="info", log_body=True)

    app.include_router(router, prefix=CONFIG.WEB_ROUTE_PREFIX)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
