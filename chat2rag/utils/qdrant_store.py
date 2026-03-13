from functools import lru_cache

from qdrant_client import AsyncQdrantClient

from chat2rag.config import CONFIG
from chat2rag.core.logger import get_logger

logger = get_logger(__name__)


@lru_cache
def get_client():
    return AsyncQdrantClient(location=CONFIG.QDRANT_LOCATION)


async def detect_vector_mode(client: AsyncQdrantClient, collection_name: str) -> str:
    """
    检测 collection 的向量模式

    Returns:
        "legacy": 旧格式（向量名 default，无 named vectors）
        "hybrid": 新格式（有 text-dense + text-sparse）
        "dense": 新格式仅 dense（有 text-dense，无 text-sparse）
    """
    if not await client.collection_exists(collection_name):
        logger.debug(
            f"Collection '{collection_name}' does not exist, will use hybrid mode"
        )
        return "hybrid"

    collection_info = await client.get_collection(collection_name)
    vectors = collection_info.config.params.vectors

    has_named_vectors = isinstance(vectors, dict)

    if not has_named_vectors:
        logger.debug(
            f"Collection '{collection_name}' uses legacy vector format (default)"
        )
        return "legacy"
    elif collection_info.config.params.sparse_vectors:
        logger.debug(
            f"Collection '{collection_name}' uses hybrid format (text-dense + text-sparse)"
        )
        return "hybrid"
    else:
        logger.debug(
            f"Collection '{collection_name}' uses dense format (text-dense only)"
        )
        return "dense"
