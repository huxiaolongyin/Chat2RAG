from functools import lru_cache

from qdrant_client import AsyncQdrantClient

from chat2rag.config import CONFIG


@lru_cache
def get_client():
    return AsyncQdrantClient(location=CONFIG.QDRANT_LOCATION)
