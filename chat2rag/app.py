import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles

from chat2rag.api.routes import router
from chat2rag.config import CONFIG
from chat2rag.core.init_app import modify_db
from chat2rag.core.logger import get_logger
from chat2rag.middleware import ExceptionHandlerMiddleware, LoggingMiddleware
from chat2rag.services.model_service import ModelSourceService, periodic_latency_update
from chat2rag.services.prompt_service import prompt_service
from chat2rag.utils.qdrant_store import get_client

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    qdrant_client = get_client()
    await modify_db()

    if CONFIG.TELEMETRY_ENABLED:
        from chat2rag.core.telemetry import setup_telemetry

        setup_telemetry()
        logger.info("Telemetry initialized")

    await prompt_service.ensure_default_prompt()

    from chat2rag.services.question_analyzer import QuestionAnalyzer

    question_analyzer = QuestionAnalyzer()
    await question_analyzer.ensure_collection()
    asyncio.create_task(question_analyzer.sync_from_metrics())

    asyncio.create_task(
        periodic_latency_update(ModelSourceService(), interval_sec=3600)
    )

    yield
    # 关闭时执行
    # await FastAPICache.clear()
    await qdrant_client.close()
    logger.info("Stopping Chat2RAG application")


def create_app():
    app = FastAPI(
        title="Chat2RAG",
        version=CONFIG.VERSION,
        lifespan=lifespan,
        docs_url=None,
    )
    # 注意顺序：异常处理在外层，日志记录在内层
    app.add_middleware(ExceptionHandlerMiddleware)
    app.add_middleware(LoggingMiddleware, log_level="info", log_body=True)

    app.include_router(router, prefix=CONFIG.WEB_ROUTE_PREFIX)

    return app


app = create_app()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount(
    "/uploads/documents", StaticFiles(directory="uploads/documents"), name="documents"
)
app.mount("/uploads/files", StaticFiles(directory="uploads/files"), name="files")


# 自定义 Swagger 文档路由
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
    )


# 自定义 OpenAPI 文档路由
@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_json():
    return app.openapi()


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=CONFIG.BACKEND_PORT, reload=False)
