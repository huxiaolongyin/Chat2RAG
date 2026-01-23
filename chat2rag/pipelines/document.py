import asyncio
import time
from typing import Any, Dict, List

from haystack import AsyncPipeline
from haystack.components.embedders import OpenAIDocumentEmbedder, OpenAITextEmbedder
from haystack.components.writers import DocumentWriter
from haystack.dataclasses import Document
from haystack.utils import Secret
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from qdrant_client.models import Filter

from chat2rag.config import CONFIG
from chat2rag.core.logger import get_logger
from chat2rag.pipelines.base import BasePipeline
from chat2rag.utils.qdrant_store import get_client

logger = get_logger(__name__)


class DocumentSearchPipeline(BasePipeline):
    """
    Create or run the document search pipeline. This pipeline is used to search for documents in the document storage.

    Args:
        qdrant_index (str): The name of the qdrant index to use.
    """

    def __init__(self, qdrant_index: str = "Document"):
        self._qdrant_index = qdrant_index
        super().__init__()

    def _initialize_pipeline(self) -> AsyncPipeline:
        """
        Initialize the Document search pipeline
        """
        try:
            pipeline = AsyncPipeline()
            embedder = OpenAITextEmbedder(
                api_base_url=CONFIG.EMBEDDING_OPENAI_URL,
                api_key=Secret.from_token(CONFIG.EMBEDDING_API_KEY),
                model=CONFIG.EMBEDDING_MODEL,
                dimensions=CONFIG.EMBEDDING_DIMENSIONS,
            )
            document_store = QdrantDocumentStore(
                location=CONFIG.QDRANT_LOCATION,
                embedding_dim=CONFIG.EMBEDDING_DIMENSIONS,
                index=self._qdrant_index,
            )
            # 替换内置client，以便在测试阶段，使用 location=':memory:' 时，能够共用实例
            document_store._async_client = get_client()
            retriever = QdrantEmbeddingRetriever(document_store=document_store)
            pipeline.add_component("embedder", embedder)
            pipeline.add_component("retriever", retriever)
            pipeline.connect("embedder.embedding", "retriever.query_embedding")
            logger.debug("The initialization of the Document search pipeline was successful.")
            return pipeline

        except Exception as e:
            logger.error(
                "Failed to initialize the Document search pipeline. Failure reason: %s",
                e,
            )
            raise

    async def run(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = CONFIG.SCORE_THRESHOLD,
        filters: Dict[str, Any] | Filter | None = None,
    ) -> dict:
        """
        Run the Document search pipeline

        Args:
            query (str): The query to search for
            top_k (int): The number of documents to be returned
            score_threshold (float): The minimum similarity score for a document to be retrieved
            filters (Dict[str, Any]): The type of documents to be retrieved.

        Returns:
            dict: The search results
        """
        logger.info(
            "Running the Document search pipeline, query: <%s>, top_k: <%s>, score_threshold: <%.2f>, filters: <%s>",
            query,
            top_k,
            score_threshold,
            filters,
        )
        start_time = time.time()
        try:
            result = await self.pipeline.run_async(
                data={
                    "embedder": {"text": query},
                    "retriever": {
                        "top_k": top_k,
                        "score_threshold": score_threshold,
                        "filters": filters,
                    },
                }
            )

            documents = result.get("retriever", {}).get("documents", [])
            logger.info(
                "Document search pipeline ran successfully. Cost: %.2f seconds, doc_counts: %d",
                time.time() - start_time,
                len(documents),
            )
            return result

        except Exception as e:
            logger.error("Failed to run the Document search pipeline. Failure reason: %s", e)
            raise


class DocumentWriterPipeline(BasePipeline):
    """
    Create or run the DocumentWriter pipeline. This pipeline is used to write documents to the document store.
    """

    def __init__(
        self,
        qdrant_index: str = "Document",
    ):
        self._qdrant_index = qdrant_index
        self.pipeline = self._initialize_pipeline()
        super().__init__()

    def _initialize_pipeline(self) -> AsyncPipeline:
        """
        Initialize the DocumentWriter pipeline
        """
        logger.debug("Initializing DocumentWriter pipeline...")
        try:
            pipeline = AsyncPipeline()
            embedder = OpenAIDocumentEmbedder(
                api_base_url=CONFIG.EMBEDDING_OPENAI_URL,
                api_key=Secret.from_token(CONFIG.EMBEDDING_API_KEY),
                model=CONFIG.EMBEDDING_MODEL,
                dimensions=CONFIG.EMBEDDING_DIMENSIONS,
            )
            document_store = QdrantDocumentStore(
                location=CONFIG.QDRANT_LOCATION,
                embedding_dim=CONFIG.EMBEDDING_DIMENSIONS,
                index=self._qdrant_index,
            )
            # 替换内置client，以便在测试阶段，使用 location=':memory:' 时，能够共用实例
            document_store._async_client = get_client()
            writer = DocumentWriter(document_store=document_store)
            pipeline.add_component("embedder", embedder)
            pipeline.add_component("writer", writer)
            pipeline.connect("embedder", "writer")
            logger.debug("DocumentWriter pipeline initialized successfully.")
            return pipeline

        except Exception as e:
            logger.error(
                "Failed to initialize the DocumentWriter pipeline. Failure reason: %s",
                e,
            )
            raise

    async def run(self, documents: List[Document]):
        """
        Run the DocumentWriter pipeline
        """
        logger.info(f"Running the DocumentWriter pipeline, documents count: <{len(documents)}>")
        try:
            result = await self.pipeline.run_async({"embedder": {"documents": documents}})
            logger.info("DocumentWriter pipeline ran successfully.")
            return result

        except Exception as e:
            logger.error("Failed to run the DocumentWriter pipeline. Failure reason: %s", e)
            raise


if __name__ == "__main__":
    doc_search_pipeline = DocumentSearchPipeline("福建省广电集团")
    print(asyncio.run(doc_search_pipeline.run("省广电五提工程")))
