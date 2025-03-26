import asyncio
import time
from typing import List

from haystack import Pipeline
from haystack.components.embedders import OpenAIDocumentEmbedder, OpenAITextEmbedder
from haystack.components.writers import DocumentWriter
from haystack.dataclasses import Document
from haystack.utils import Secret
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore

from chat2rag.config import CONFIG
from chat2rag.logger import get_logger
from chat2rag.pipelines.base import BasePipeline

logger = get_logger(__name__)

# 监控
# from chat2rag.telemetry import setup_telemetry

# setup_telemetry()


class DocumentSearchPipeline(BasePipeline):
    """
    Create or run a document search pipeline. This pipeline is used to search for documents in a document store.
    Args:
        qdrant_index (str): The name of the qdrant index to use.
    """

    def __init__(
        self,
        qdrant_index: str = "Document",
    ):
        self._qdrant_index = qdrant_index
        self.pipeline = self._initialize_pipeline()
        super().__init__()

    def _initialize_pipeline(self):
        """
        Initialize the document search pipeline
        """
        logger.debug("Initialize document search pipeline...")
        try:
            pipeline = Pipeline()
            embedder = OpenAITextEmbedder(
                api_base_url=CONFIG.EMBEDDING_OPENAI_URL,
                api_key=Secret.from_env_var("OPENAI_API_KEY"),
                model=CONFIG.EMBEDDING_MODEL,
                dimensions=CONFIG.EMBEDDING_DIMENSIONS,
            )
            retriever = QdrantEmbeddingRetriever(
                document_store=QdrantDocumentStore(
                    host=CONFIG.QDRANT_HOST,
                    port=CONFIG.QDRANT_PORT,
                    embedding_dim=CONFIG.EMBEDDING_DIMENSIONS,
                    index=self._qdrant_index,
                )
            )
            pipeline.add_component("embedder", embedder)
            pipeline.add_component("retriever", retriever)
            pipeline.connect("embedder.embedding", "retriever.query_embedding")
            logger.debug("Document search pipeline initialized successfully.")
            return pipeline

        except Exception as e:
            logger.error("Failed to initialize document search pipeline: %s", e)
            raise

    def warm_up(self):
        """
        Warm up the document search pipeline by loading necessary models and resources
        """
        logger.debug("Warm up the document search pipeline...")
        try:
            self.pipeline.warm_up()
            logger.debug("Document search warm up successfully")

        except Exception as e:
            logger.error("Failed to warm up document search pipeline: %s", e)
            raise

    async def run(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = CONFIG.SCORE_THRESHOLD,
        doc_type: str = "qa_pair",
    ) -> dict:
        """
        Run the document search pipeline
        Args:
            query (str): The query to search for.
            top_k (int): The number of documents to return.
        Returns:
            dict: The search results.
        """
        logger.info(
            "Run the document search pipeline, query: <%s>, top_k: <%s>, score_threshold: <%.2f>, doc_type: <%s>",
            query,
            top_k,
            score_threshold,
            doc_type,
        )
        start_time = time.time()
        try:
            result = await asyncio.to_thread(
                self.pipeline.run,
                data={
                    "embedder": {"text": query},
                    "retriever": {
                        "top_k": top_k,
                        "score_threshold": score_threshold,
                        "filters": {
                            "field": "meta.type",
                            "operator": "==",
                            "value": doc_type,
                        },
                    },
                },
            )
            logger.info(
                "Document search pipeline ran successfully in %.2f seconds",
                time.time() - start_time,
            )
            return result

        except Exception as e:
            logger.error("Failed to run document search pipeline: %s", e)
            raise


class DocumentWriterPipeline(BasePipeline):
    """
    Create or run a document writer pipeline. This pipeline is used to write documents to a document store.
    """

    def __init__(
        self,
        qdrant_index: str = "Document",
    ):
        self._qdrant_index = qdrant_index
        self.pipeline = self._initialize_pipeline()
        super().__init__()

    def _initialize_pipeline(self):
        """
        Initialize the document writer pipeline
        """
        logger.debug("Initializing document writer pipeline...")
        try:
            pipeline = Pipeline()
            embedder = OpenAIDocumentEmbedder(
                api_base_url=CONFIG.EMBEDDING_OPENAI_URL,
                api_key=Secret.from_env_var("OPENAI_API_KEY"),
                model=CONFIG.EMBEDDING_MODEL,
                dimensions=CONFIG.EMBEDDING_DIMENSIONS,
            )
            writer = DocumentWriter(
                document_store=QdrantDocumentStore(
                    host=CONFIG.QDRANT_HOST,
                    port=CONFIG.QDRANT_PORT,
                    embedding_dim=CONFIG.EMBEDDING_DIMENSIONS,
                    index=self._qdrant_index,
                ),
            )
            pipeline.add_component("embedder", embedder)
            pipeline.add_component("writer", writer)
            pipeline.connect("embedder", "writer")
            logger.debug("Document writer pipeline initialized successfully.")
            return pipeline

        except Exception as e:
            logger.error("Failed to initialize document writer pipeline: %s", e)
            raise

    def warm_up(self):
        """
        Warm up the document writer pipeline by loading necessary models and resources
        """
        logger.debug("Warm up the document writer pipeline...")
        try:
            self.pipeline.warm_up()
            logger.debug("Document writer warm up successfully")

        except Exception as e:
            logger.error("Failed to warm up document writer pipeline: %s", e)
            raise

    async def run(self, documents: List[Document]):
        """
        Running the document writer pipeline
        """
        logger.info(
            f"Running document writer pipeline with documents: <{','.join([item.content for item in documents])}>"
        )
        try:
            result = await asyncio.to_thread(
                self.pipeline.run, data={"embedder": {"documents": documents}}
            )
            logger.info("Document writer pipeline ran successfully")
            return result
        except Exception as e:
            logger.error("Failed to run document writer pipeline: %s", e)
            raise
