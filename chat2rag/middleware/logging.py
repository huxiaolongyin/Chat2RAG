import json
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from chat2rag.logger import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志记录中间件"""

    def __init__(self, app, log_level: str = "info", log_body: bool = True):
        super().__init__(app)
        self.log_level = log_level
        self.log_body = log_body

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # 提取请求信息
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)

        # 获取请求体（可选）
        body_params = {}
        if self.log_body and method in ["POST", "PUT", "PATCH"]:
            try:
                if request.headers.get("content-type", "").startswith("application/json"):
                    body = await request.body()
                    if body:
                        body_params = json.loads(body.decode())
                        request._body = body
            except Exception:
                body_params = {"error": "无法解析请求体"}

        # 记录请求开始
        params_info = {"query": query_params}
        if body_params:
            params_info["body"] = body_params

        log_msg = f"{method} {path} - params: {params_info}"

        if self.log_level == "info":
            logger.info(log_msg)
        elif self.log_level == "debug":
            logger.debug(log_msg)

        # 执行请求
        response = await call_next(request)

        # 记录响应
        process_time = time.time() - start_time
        logger.info(f"{method} {path} - 状态码: {response.status_code} - " f"处理时间: {process_time:.3f}s")

        return response
