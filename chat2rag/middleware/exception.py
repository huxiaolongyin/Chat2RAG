import uuid
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from chat2rag.core.exceptions import (
    BusinessException,
    ParameterException,
    ValueAlreadyExist,
    ValueNoExist,
)
from chat2rag.core.logger import get_logger

logger = get_logger(__name__)


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """Unified exception handling middleware"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)

        except ValueNoExist as e:
            logger.warning(
                f"Resource not found: {e.msg}",
                extra={"path": request.url.path, "method": request.method},
            )
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": e.msg})

        except ValueAlreadyExist as e:
            logger.warning(
                f"Resource already exists: {e.msg}",
                extra={"path": request.url.path, "method": request.method},
            )
            return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": e.msg})

        except ParameterException as e:
            logger.warning(
                f"Invalid parameter: {e.msg}",
                extra={"path": request.url.path, "method": request.method},
            )
            return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": e.msg})

        except BusinessException as e:
            logger.warning(
                f"Business error: {e.msg}",
                extra={"path": request.url.path, "method": request.method},
            )
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": e.msg})

        except Exception as e:
            error_id = str(uuid.uuid4())[:8].upper()

            logger.error(
                f"Unexpected error [{error_id}]: {type(e).__name__}",
                exc_info=True,
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "error_id": error_id,
                },
            )

            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": f"Internal server error (Error ID: {error_id})"},
            )
