import asyncio
import time
from typing import Any, Dict, List

from haystack import AsyncPipeline, component
from haystack.components.embedders import (
    OpenAIDocumentEmbedder,
    OpenAITextEmbedder,
    SentenceTransformersSparseDocumentEmbedder,
    SentenceTransformersSparseTextEmbedder,
)
from haystack.components.writers import DocumentWriter
from haystack.dataclasses import Document
from haystack.dataclasses.sparse_embedding import SparseEmbedding
from haystack.utils import Secret
from haystack_integrations.components.retrievers.qdrant import (
    QdrantEmbeddingRetriever,
    QdrantHybridRetriever,
)
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from qdrant_client.models import Filter

from chat2rag.config import CONFIG
from chat2rag.core.logger import get_logger
from chat2rag.pipelines.base import BasePipeline
from chat2rag.utils.qdrant_store import detect_vector_mode, get_client

logger = get_logger(__name__)


class CustomerSparseDocumentEmbedder(SentenceTransformersSparseDocumentEmbedder):
    @component.output_types(documents=list[Document])
    async def run_async(self, documents: list[Document]):
        return super().run(documents)


class CustomerSparseTextEmbedder(SentenceTransformersSparseTextEmbedder):
    @component.output_types(sparse_embedding=SparseEmbedding)
    async def run_async(self, text: str):
        return super().run(text)


class DocumentSearchPipeline(BasePipeline):
    """
    Create or run the document search pipeline. This pipeline is used to search for documents in the document storage.

    Args:
        qdrant_index (str): The name of the qdrant index to use.
        retrieval_mode (str): The retrieval mode, either "hybrid" or "dense". Defaults to CONFIG.RETRIEVAL_MODE.
    """

    def __init__(
        self, qdrant_index: str = "Document", retrieval_mode: str | None = None
    ):
        super().__init__()
        self._qdrant_index = qdrant_index
        self._retrieval_mode = retrieval_mode or CONFIG.RETRIEVAL_MODE
        if self._retrieval_mode not in ("hybrid", "dense"):
            raise ValueError(
                f"Invalid retrieval_mode: {self._retrieval_mode}, must be 'hybrid' or 'dense'"
            )
        self._vector_mode: str | None = None

    async def _prepare_async_resources(self):
        """检测 collection 的向量模式"""
        client = get_client()
        self._vector_mode = await detect_vector_mode(client, self._qdrant_index)
        logger.info(
            f"Detected vector mode for '{self._qdrant_index}': {self._vector_mode}"
        )

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

            use_sparse = self._vector_mode == "hybrid"
            use_hybrid_retriever = use_sparse and self._retrieval_mode == "hybrid"

            document_store = QdrantDocumentStore(
                location=CONFIG.QDRANT_LOCATION,
                embedding_dim=CONFIG.EMBEDDING_DIMENSIONS,
                index=self._qdrant_index,
                use_sparse_embeddings=use_sparse,
            )

            document_store._async_client = get_client()

            pipeline.add_component("embedder", embedder)

            if use_hybrid_retriever:
                sparse_embedder = CustomerSparseTextEmbedder(
                    model="C:/Users/Administrator/code/opensearch-neural-sparse-encoding-multilingual-v1"
                )
                retriever = QdrantHybridRetriever(document_store=document_store)
                pipeline.add_component("sparse_embedder", sparse_embedder)
                pipeline.add_component("retriever", retriever)
                pipeline.connect("embedder.embedding", "retriever.query_embedding")
                pipeline.connect("sparse_embedder", "retriever.query_sparse_embedding")
            else:
                retriever = QdrantEmbeddingRetriever(document_store=document_store)
                pipeline.add_component("retriever", retriever)
                pipeline.connect("embedder.embedding", "retriever.query_embedding")

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
            top_k (int): The number of documents to be returned
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
            data = {
                "embedder": {"text": query},
                "retriever": {
                    "top_k": top_k,
                    "score_threshold": score_threshold,
                    "filters": filters,
                },
            }
            if self._vector_mode == "hybrid" and self._retrieval_mode == "hybrid":
                data["sparse_embedder"] = {"text": query}

            result = await self.pipeline.run_async(data=data)

            documents = result.get("retriever", {}).get("documents", [])
            logger.info(
                f"Document search completed: found {len(documents)} documents in {time.time() - start_time:.2f}s"
            )
            return result

        except Exception as e:
            logger.exception("Failed to run Document search pipeline")
            raise


class DocumentWriterPipeline(BasePipeline):
    """
    Create or run the DocumentWriter pipeline. This pipeline is used to write documents to the document store.
    """

    def __init__(
        self,
        qdrant_index: str = "Document",
    ):
        super().__init__()
        self._qdrant_index = qdrant_index
        self._vector_mode: str | None = None

    async def _prepare_async_resources(self):
        """检测 collection 的向量模式"""
        client = get_client()
        self._vector_mode = await detect_vector_mode(client, self._qdrant_index)
        logger.info(
            f"Detected vector mode for '{self._qdrant_index}': {self._vector_mode}"
        )

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

            if use_sparse:
                sparse_embedder = CustomerSparseDocumentEmbedder(
                    model="C:/Users/Administrator/code/opensearch-neural-sparse-encoding-multilingual-v1"
                )
                pipeline.add_component("sparse_embedder", sparse_embedder)
                pipeline.connect("embedder", "sparse_embedder")
                pipeline.connect("sparse_embedder", "writer")
            else:
                pipeline.add_component("writer", writer)
                pipeline.connect("embedder", "writer")

            logger.debug("DocumentWriter pipeline initialized successfully.")
            return pipeline

        except Exception as e:
            logger.exception("Failed to initialize DocumentWriter pipeline")
            raise

    async def run(self, documents: List[Document]):
        """
        Run the DocumentWriter pipeline
        """
        logger.info(f"Document writer started: {len(documents)} documents")
        try:
            result = await self.pipeline.run_async(
                {"embedder": {"documents": documents}}
            )
            logger.info("Document writer completed")
            return result

        except Exception as e:
            logger.exception("Failed to run DocumentWriter pipeline")
            raise


if __name__ == "__main__":
    import asyncio

    pipeline = DocumentSearchPipeline("test")
    # # print(pipeline)
    # documents = [
    #     Document(
    #         content="医生会根据情况给予黏膜保护剂或表面麻醉剂，目的是保护食管黏膜和缓解疼痛。有呕吐、呕血者医生会适当使用镇吐、止血与镇静药物"
    #     ),
    #     Document(content="医生会通过鼻饲或静脉给予患者营养支持，促进疾病恢复。\n怎么预防放射性食管炎"),
    #     Document(content="Germany has many big cities"),
    #     Document(content="fastembed is supported by and maintained by Qdrant."),
    # ]
    print(asyncio.run(pipeline.run(query="水温", score_threshold=0.5)))
