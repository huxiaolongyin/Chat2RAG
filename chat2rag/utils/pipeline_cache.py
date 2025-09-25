from functools import lru_cache
from typing import Any, Type, TypeVar

from chat2rag.logger import get_logger

logger = get_logger(__name__)
T = TypeVar("T")


def _make_hashable_kwargs(**kwargs) -> tuple:
    """Convert kwargs into a hashable tuple, suitable for lru_cache."""
    items = []
    for k, v in sorted(kwargs.items()):
        if isinstance(v, list):
            v = tuple(v)
        elif isinstance(v, dict):
            v = tuple(sorted(_make_hashable_kwargs(**v)))
        elif isinstance(v, (str, int, float, bool, type(None))):
            pass
        else:
            # 对于函数、对象等，使用其 repr 或 id（谨慎！）
            v = str(v)  # 或 hash(v) if v is already hashable
        items.append((k, v))
    return tuple(items)


@lru_cache(maxsize=32)
def _cached_create_pipeline(cls: Type[T], args: tuple, hashable_kwargs: tuple) -> T:
    """实际被缓存的工厂函数"""
    kwargs = dict(hashable_kwargs)
    # 注意：这里假设值已经是构造所需类型（如 str, int），否则需反序列化
    return cls(*args, **kwargs)


def create_pipeline(cls: Type[T], *args: Any, **kwargs: Any) -> T:
    """
    Generic cached pipeline creator.
    Converts kwargs to hashable format before caching.
    """
    try:
        hashable_kwargs = _make_hashable_kwargs(**kwargs)
        return _cached_create_pipeline(cls, args, hashable_kwargs)
    except Exception as e:
        logger.warning(f"Failed to create the cache pipeline：{e}")
        return cls(args, **kwargs)
