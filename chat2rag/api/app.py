from fastapi import FastAPI

from chat2rag.api.routes import router
from chat2rag.config import CONFIG
from chat2rag.database.init_db import run_migrations
from chat2rag.logger import logger
from chat2rag.tools.tool_manager import ToolManager

# from chat2rag.api.v1 import ws_router


# @asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    # FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")
    logger.info("正在应用数据库迁移...")
    migration_success = run_migrations()

    if not migration_success:
        logger.error("数据库迁移失败，应用可能无法正常运行")
        # 视情况决定是否继续
        # return False

    logger.info("数据库设置完成")
    # 进行 RAG 流程监控
    if CONFIG.TELEMETRY_ENABLED:
        from chat2rag.telemetry import setup_telemetry

        logger.info("Setting up telemetry...")
        # 需要先启动 server 服务： python -m phoenix.server.main serve
        setup_telemetry()
        logger.info("Telemetry setup successfully")

    # 加载MCP连接
    ToolManager()

    yield
    # 关闭时执行
    # await FastAPICache.clear()
    logger.info("Stopping Chat2RAG application")


def create_app():
    app = FastAPI(title="Chat2RAG", version=CONFIG.VERSION, lifespan=lifespan)
    app.include_router(router, prefix=CONFIG.WEB_ROUTE_PREFIX)
    # app.include_router(ws_router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "chat2rag.api.app:app",
        host="0.0.0.0",
        port=CONFIG.BACKEND_PORT,
        reload=False,
    )
