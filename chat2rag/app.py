import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles

from chat2rag.api.routes import router
from chat2rag.config import CONFIG
from chat2rag.core.init_app import modify_db
from chat2rag.logger import get_logger
from chat2rag.services.model_service import ModelSourceService, periodic_latency_update
from chat2rag.services.prompt_service import prompt_service

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):

    await modify_db()  # 数据库自动迁移

    # 进行 RAG 流程监控
    if CONFIG.TELEMETRY_ENABLED:
        from chat2rag.telemetry import setup_telemetry

        logger.info("Setting up telemetry...")
        # 需要先启动 server 服务： python -m phoenix.server.main serve
        setup_telemetry()
        logger.info("Telemetry setup successfully")

    # 创建默认提示词
    await prompt_service.ensure_default_prompt()

    # 加载MCP连接
    # ToolManager()
    asyncio.create_task(
        periodic_latency_update(ModelSourceService(), interval_sec=3600)
    )

    yield
    # 关闭时执行
    # await FastAPICache.clear()

    logger.info("Stopping Chat2RAG application")


def create_app():
    app = FastAPI(
        title="Chat2RAG",
        version=CONFIG.VERSION,
        lifespan=lifespan,
        docs_url=None,
    )
    app.include_router(router, prefix=CONFIG.WEB_ROUTE_PREFIX)

    return app


app = create_app()
app.mount("/static", StaticFiles(directory="static"), name="static")  # 加载静态文件


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
