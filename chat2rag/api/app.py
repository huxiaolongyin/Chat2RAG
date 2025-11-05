from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles

from chat2rag.api.routes import router
from chat2rag.config import CONFIG
from chat2rag.core.init_app import modify_db
from chat2rag.logger import get_logger

# from chat2rag.tools.tool_manager import ToolManager

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 数据库自动迁移
    await modify_db()

    # 进行 RAG 流程监控
    if CONFIG.TELEMETRY_ENABLED:
        from chat2rag.telemetry import setup_telemetry

        logger.info("Setting up telemetry...")
        # 需要先启动 server 服务： python -m phoenix.server.main serve
        setup_telemetry()
        logger.info("Telemetry setup successfully")

    # 加载MCP连接
    # ToolManager()

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
# 加载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")


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
    import uvicorn

    uvicorn.run(
        "chat2rag.api.app:app",
        host="0.0.0.0",
        port=CONFIG.BACKEND_PORT,
        reload=False,
    )
