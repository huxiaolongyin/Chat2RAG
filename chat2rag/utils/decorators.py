import functools
from typing import Any, Callable

from fastapi import HTTPException, status

from chat2rag.exceptions import BusinessException, ValueAlreadyExist, ValueNoExist
from chat2rag.logger import get_logger

logger = get_logger(__name__)


def exception_handler(func: Callable) -> Callable:
    """改进的API异常处理"""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        try:
            return await func(*args, **kwargs)

        except ValueNoExist as e:
            logger.warning(
                f"资源不存在: {e.msg}",
                extra={"function": func.__name__, "error_type": "ValueNoExist"},
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.msg)

        except ValueAlreadyExist as e:
            logger.warning(
                f"资源已存在: {e.msg}",
                extra={"function": func.__name__, "error_type": "ValueAlreadyExist"},
            )
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.msg)

        except BusinessException as e:
            logger.warning(
                f"业务异常: {e.msg}",
                extra={"function": func.__name__, "error_type": "BusinessException"},
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.msg)

        except HTTPException:
            raise

        except Exception as e:
            # 添加更多调试信息
            error_id = f"ERR_{func.__name__}_{hash(str(e)) % 10000:04d}"
            logger.error(
                f"系统异常 [{error_id}]: {str(e)}",
                exc_info=True,
                extra={"function": func.__name__, "error_id": error_id},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"系统内部错误，请稍后重试 (错误ID: {error_id})",
            )

    return wrapper
