import functools
import time
from typing import Callable

from chat2rag.logger import get_logger

logger = get_logger(__name__)


# 性能监控装饰器
def async_performance_logger(func: Callable):
    @functools.wraps(func)  # 保留原始函数的签名和元数据
    async def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = await func(*args, **kwargs)
        elapsed_time = time.perf_counter() - start_time
        logger.debug(
            f"API Function <{func.__name__}> took {elapsed_time:.3f} seconds to complete"
        )
        return result

    return wrapper
