from fastapi import FastAPI

from chat2rag.api.routes import router
from chat2rag.config import CONFIG
from chat2rag.logger import logger
from chat2rag.pipelines.rag import RAGPipeline


# @asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    # FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")

    # 进行 RAG 流程监控
    if CONFIG.TELEMETRY_ENABLED:
        from chat2rag.telemetry import setup_telemetry

        logger.info("Setting up telemetry...")
        # 需要先启动 server 服务： python -m phoenix.server.main serve
        setup_telemetry()
        logger.info("Telemetry setup successfully")

    # logger.info("Starting Chat2RAG application")
    # 预热 RAG 管道
    RAGPipeline("Document")
    yield
    # 关闭时执行
    # await FastAPICache.clear()
    logger.info("Stopping Chat2RAG application")


def create_app():
    app = FastAPI(title="Chat2RAG", version=CONFIG.VERSION, lifespan=lifespan)
    app.include_router(router, prefix=CONFIG.WEB_ROUTE_PREFIX)

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
