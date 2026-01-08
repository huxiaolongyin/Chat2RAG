import traceback
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from chat2rag.exceptions import BusinessException, ValueAlreadyExist, ValueNoExist
from chat2rag.logger import get_logger

logger = get_logger(__name__)


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """统一异常处理中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)

        except ValueNoExist as e:
            logger.warning(
                f"资源不存在: {e.msg}",
                extra={"path": request.url.path, "method": request.method, "error_type": "ValueNoExist"},
            )
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": e.msg})

        except ValueAlreadyExist as e:
            logger.warning(
                f"资源已存在: {e.msg}",
                extra={"path": request.url.path, "method": request.method, "error_type": "ValueAlreadyExist"},
            )
            return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": e.msg})

        except BusinessException as e:
            logger.warning(
                f"业务异常: {e.msg}",
                extra={"path": request.url.path, "method": request.method, "error_type": "BusinessException"},
            )
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": e.msg})

        except Exception as e:
            error_id = f"ERR_{request.url.path.replace('/', '_')}_{hash(str(e)) % 10000:04d}"

            logger.error(
                f"系统异常 [{error_id}]: {str(e)}",
                exc_info=True,
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "error_id": error_id,
                    "traceback": traceback.format_exc(),
                },
            )

            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": f"系统内部错误，请稍后重试 (错误ID: {error_id})"},
            )
