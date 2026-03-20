import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from chat2rag.core.logger import get_logger
from chat2rag.schemas.document import DocumentData

logger = get_logger(__name__)

DEFAULT_EXPIRE_MINUTES = 30


class PreviewCache:
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cache: dict = {}
            cls._instance._cleanup_task: Optional[asyncio.Task] = None
        return cls._instance

    @classmethod
    def get_instance(cls) -> "PreviewCache":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    def generate_cache_key(content: bytes, max_chars: int, overlap: int) -> str:
        content_hash = hashlib.md5(content).hexdigest()[:16]
        return f"{content_hash}_{max_chars}_{overlap}"

    @staticmethod
    def generate_preview_id() -> str:
        return str(uuid4())

    async def set(
        self,
        content: bytes,
        max_chars: int,
        overlap: int,
        doc_list: list[DocumentData],
        expire_minutes: int = DEFAULT_EXPIRE_MINUTES,
    ) -> str:
        cache_key = self.generate_cache_key(content, max_chars, overlap)
        preview_id = self.generate_preview_id()
        expire_time = datetime.now() + timedelta(minutes=expire_minutes)

        async with self._lock:
            self._cache[preview_id] = {
                "cache_key": cache_key,
                "doc_list": doc_list,
                "expire_time": expire_time,
                "created_at": datetime.now(),
            }

        logger.info(
            f"预览缓存已创建: preview_id={preview_id}, cache_key={cache_key}, chunks={len(doc_list)}"
        )
        return preview_id

    async def get(
        self,
        preview_id: str,
        content: bytes,
        max_chars: int,
        overlap: int,
    ) -> Optional[list[DocumentData]]:
        async with self._lock:
            cache_entry = self._cache.get(preview_id)

            if not cache_entry:
                logger.warning(f"预览缓存不存在: preview_id={preview_id}")
                return None

            if datetime.now() > cache_entry["expire_time"]:
                del self._cache[preview_id]
                logger.warning(f"预览缓存已过期: preview_id={preview_id}")
                return None

            expected_key = self.generate_cache_key(content, max_chars, overlap)
            if cache_entry["cache_key"] != expected_key:
                logger.warning(
                    f"预览缓存key不匹配: preview_id={preview_id}, "
                    f"expected={expected_key}, actual={cache_entry['cache_key']}"
                )
                return None

            doc_list = cache_entry["doc_list"]
            del self._cache[preview_id]
            logger.info(
                f"预览缓存命中并已清理: preview_id={preview_id}, chunks={len(doc_list)}"
            )
            return doc_list

    async def delete(self, preview_id: str) -> bool:
        async with self._lock:
            if preview_id in self._cache:
                del self._cache[preview_id]
                logger.info(f"预览缓存已删除: preview_id={preview_id}")
                return True
            return False

    async def cleanup_expired(self) -> int:
        now = datetime.now()
        expired_keys = []

        async with self._lock:
            for preview_id, entry in list(self._cache.items()):
                if now > entry["expire_time"]:
                    expired_keys.append(preview_id)

            for key in expired_keys:
                del self._cache[key]

        if expired_keys:
            logger.info(f"清理过期预览缓存: {len(expired_keys)} 条")

        return len(expired_keys)

    async def start_cleanup_task(self, interval_seconds: int = 300):
        if self._cleanup_task and not self._cleanup_task.done():
            return

        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(interval_seconds)
                    await self.cleanup_expired()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.exception(f"清理任务异常: {e}")

        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info(f"预览缓存清理任务已启动，间隔 {interval_seconds} 秒")


preview_cache = PreviewCache.get_instance()
