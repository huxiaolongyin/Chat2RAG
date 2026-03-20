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

from chat2rag.components import OpenRanker
from chat2rag.config import CONFIG
from chat2rag.core.logger import get_logger
from chat2rag.pipelines.base import BasePipeline
from chat2rag.utils.qdrant_store import detect_vector_mode, get_client

logger = get_logger(__name__)


class DocumentSearchPipeline(BasePipeline):
    def __init__(self, qdrant_index: str = "Document"):
        super().__init__()
        self._qdrant_index = qdrant_index
        self._vector_mode: str | None = None

    async def _prepare_async_resources(self):
        client = get_client()
        self._vector_mode = await detect_vector_mode(client, self._qdrant_index)
        logger.info(f"Detected vector mode for '{self._qdrant_index}': {self._vector_mode}")

    def _initialize_pipeline(self) -> AsyncPipeline:
        try:
            pipeline = AsyncPipeline()
            embedder = OpenAITextEmbedder(
                api_base_url=CONFIG.EMBEDDING_OPENAI_URL,
                api_key=Secret.from_token(CONFIG.EMBEDDING_API_KEY),
                model=CONFIG.EMBEDDING_MODEL,
                dimensions=CONFIG.EMBEDDING_DIMENSIONS,
            )

            use_sparse = self._vector_mode in ("hybrid", "dense")

            document_store = QdrantDocumentStore(
                location=CONFIG.QDRANT_LOCATION,
                embedding_dim=CONFIG.EMBEDDING_DIMENSIONS,
                index=self._qdrant_index,
                use_sparse_embeddings=use_sparse,
            )

            document_store._async_client = get_client()

            retriever = QdrantEmbeddingRetriever(document_store=document_store)

            pipeline.add_component("embedder", embedder)
            pipeline.add_component("retriever", retriever)
            pipeline.connect("embedder.embedding", "retriever.query_embedding")

            if CONFIG.RERANK_ENABLED:
                ranker = OpenRanker(
                    model=CONFIG.RERANK_MODEL,
                    top_k=CONFIG.TOP_K,
                    api_key=Secret.from_token(CONFIG.RERANK_API_KEY) if CONFIG.RERANK_API_KEY else None,
                    api_base_url=CONFIG.RERANK_URL,
                )
                pipeline.add_component("ranker", ranker)
                pipeline.connect("retriever.documents", "ranker.documents")

            return pipeline

        except Exception as e:
            logger.exception("Failed to initialize Document search pipeline")
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
            top_k (int): The number of documents to be returned (after rerank)
            score_threshold (float): The minimum similarity score for a document to be retrieved
            filters (Dict[str, Any]): The type of documents to be retrieved.

        Returns:
            dict: The search results
        """
        logger.info(
            f"Document search started: query='{query}', top_k={top_k}, score_threshold={score_threshold:.2f}, filters={filters}"
        )
        start_time = time.time()
        try:
            run_data = {
                "embedder": {"text": query},
                "retriever": {
                    "top_k": CONFIG.DENSE_TOP_K if CONFIG.RERANK_ENABLED else top_k,
                    "score_threshold": score_threshold,
                    "filters": filters,
                },
            }

            if CONFIG.RERANK_ENABLED:
                run_data["ranker"] = {"query": query, "top_k": top_k}

            result = await self.pipeline.run_async(data=run_data)

            output_key = "ranker" if CONFIG.RERANK_ENABLED else "retriever"
            documents = result.get(output_key, {}).get("documents", [])
            logger.info(
                f"Document search completed: found {len(documents)} documents in {time.time() - start_time:.2f}s"
            )
            return result

        except Exception as e:
            logger.exception("Failed to run Document search pipeline")
            raise


class DocumentWriterPipeline(BasePipeline):
    def __init__(self, qdrant_index: str = "Document"):
        super().__init__()
        self._qdrant_index = qdrant_index
        self._vector_mode: str | None = None

    async def _prepare_async_resources(self):
        client = get_client()
        self._vector_mode = await detect_vector_mode(client, self._qdrant_index)
        logger.info(f"Detected vector mode for '{self._qdrant_index}': {self._vector_mode}")

    def _initialize_pipeline(self) -> AsyncPipeline:
        logger.debug("Initializing DocumentWriter pipeline...")
        try:
            pipeline = AsyncPipeline()

            embedder = OpenAIDocumentEmbedder(
                api_base_url=CONFIG.EMBEDDING_OPENAI_URL,
                api_key=Secret.from_token(CONFIG.EMBEDDING_API_KEY),
                model=CONFIG.EMBEDDING_MODEL,
                dimensions=CONFIG.EMBEDDING_DIMENSIONS,
            )

            use_sparse = self._vector_mode in ("hybrid", "dense")
            document_store = QdrantDocumentStore(
                location=CONFIG.QDRANT_LOCATION,
                embedding_dim=CONFIG.EMBEDDING_DIMENSIONS,
                use_sparse_embeddings=use_sparse,
                index=self._qdrant_index,
            )
            document_store._async_client = get_client()
            writer = DocumentWriter(document_store=document_store)

            pipeline.add_component("embedder", embedder)
            pipeline.add_component("writer", writer)
            pipeline.connect("embedder", "writer")

            logger.debug("DocumentWriter pipeline initialized successfully.")
            return pipeline

        except Exception as e:
            logger.exception("Failed to initialize DocumentWriter pipeline")
            raise

    async def run(self, documents: List[Document]):
        logger.info(f"Document writer started: {len(documents)} documents")
        try:
            result = await self.pipeline.run_async({"embedder": {"documents": documents}})
            logger.info("Document writer completed")
            return result

        except Exception as e:
            logger.exception("Failed to run DocumentWriter pipeline")
            raise
