import asyncio
from time import perf_counter
from typing import List, Union

from haystack import Pipeline
from haystack.components.embedders import OpenAIDocumentEmbedder, OpenAITextEmbedder
from haystack.components.writers import DocumentWriter
from haystack.dataclasses import Document
from haystack.utils import Secret
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore

from rag_core.config import CONFIG
from rag_core.logging import logger

# from pyinstrument import Profiler


class DocumentSearchPipeline:
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
        self._initialize_pipeline()
        self.warm_up()

    def __str__(self):
        return str(self.pipeline)

    def __repr__(self):
        return str(self.pipeline)

    def _create_retriever(self):
        """
        Create a retriever for the document search pipeline
        """
        logger.info(f"Creating retriever with qdrant index <{self._qdrant_index}>...")

        retriever = QdrantEmbeddingRetriever(
            document_store=QdrantDocumentStore(
                host=CONFIG.QDRANT_HOST,
                port=CONFIG.QDRANT_PORT,
                embedding_dim=CONFIG.EMBEDDING_DIMENSIONS,
                index=self._qdrant_index,
            )
        )

        logger.info(
            f"Retriever with qdrant index <{self._qdrant_index}> created successfully"
        )

        return retriever

    def _initialize_pipeline(self):
        """
        Initialize the document search pipeline
        """
        logger.info(
            f"Initializing document search pipeline with qdrant index <{self._qdrant_index}>..."
        )

        embedder = OpenAITextEmbedder(
            api_base_url=CONFIG.EMBEDDING_OPENAI_URL,
            api_key=Secret.from_env_var("OPENAI_API_KEY"),
            model=CONFIG.EMBEDDING_MODEL,
            dimensions=CONFIG.EMBEDDING_DIMENSIONS,
        )
        retriever = self._create_retriever()
        self.pipeline = Pipeline()
        self.pipeline.add_component("embedder", embedder)
        self.pipeline.add_component("retriever", retriever)
        self.pipeline.connect("embedder.embedding", "retriever.query_embedding")

        logger.info(
            f"Document search pipeline with qdrant index <{self._qdrant_index}> initialized successfully"
        )

    def warm_up(self):
        """
        Warm up the document search pipeline
        """
        logger.info(
            f"Warming up document search pipeline with qdrant index <{self._qdrant_index}>..."
        )
        self.pipeline.warm_up()
        logger.info(
            f"Document search pipeline with qdrant index <{self._qdrant_index}> warmed up successfully"
        )

    async def run(
        self,
        query: str,
        top_k: int = CONFIG.TOP_K,
        score_threshold: float = CONFIG.SCORE_THRESHOLD,
        start=perf_counter(),
        type: str = "qa_pair",
    ):
        """
        Excute the document search pipeline
        """
        # profiler = Profiler()
        # profiler.start()

        logger.info(
            f"Running document search pipeline with query: <{query}>, qdrant index: <{self._qdrant_index}>..."
        )

        result = await asyncio.to_thread(
            self.pipeline.run,
            {
                "embedder": {"text": query},
                "retriever": {
                    "top_k": top_k,
                    "score_threshold": score_threshold,
                    "filters": {
                        "field": "meta.type",
                        "operator": "==",
                        "value": type,
                    },
                },
            },
        )

        logger.info(
            f"Document search pipeline ran successfully with query: <{query}>; Total: <{len(result['retriever']['documents'])}>; Cost: {perf_counter() - start:.3f} s"
        )
        # profiler.stop()
        # print(profiler.output_text(unicode=True, color=True))
        return result


class DocumentWriterPipeline:
    """
    Create or run a document writer pipeline. This pipeline is used to write documents to a document store.
    """

    def __init__(
        self,
        qdrant_index: str,
    ):
        self._qdrant_index = qdrant_index
        self._initialize_pipeline()
        self.warm_up()

    def __str__(self):
        return str(self.pipeline)

    def __repr__(self):
        return str(self.pipeline)

    def _create_writer(self):
        """
        Create a writer for the document writer pipeline
        """
        logger.info(f"Creating writer with qdrant index <{self._qdrant_index}>...")

        writer = DocumentWriter(
            document_store=QdrantDocumentStore(
                host=CONFIG.QDRANT_HOST,
                port=CONFIG.QDRANT_PORT,
                embedding_dim=CONFIG.EMBEDDING_DIMENSIONS,
                index=self._qdrant_index,
            )
        )
        logger.info(
            f"Document writer with qdrant index <{self._qdrant_index}> created successfully"
        )

        return writer

    def _initialize_pipeline(self):
        """
        Initialize the document writer pipeline
        """
        logger.info("Initializing document writer pipeline...")
        embedder = OpenAIDocumentEmbedder(
            api_base_url=CONFIG.EMBEDDING_OPENAI_URL,
            api_key=Secret.from_env_var("OPENAI_API_KEY"),
            model=CONFIG.EMBEDDING_MODEL,
            dimensions=CONFIG.EMBEDDING_DIMENSIONS,
        )
        writer = self._create_writer()
        self.pipeline = Pipeline()
        self.pipeline.add_component("embedder", embedder)
        self.pipeline.add_component("writer", writer)
        self.pipeline.connect("embedder", "writer")

        logger.info("Document writer pipeline initialized successfully.")

    def warm_up(self):
        """
        Warm up the document writer pipeline
        """
        logger.info(
            f"Warming up document writer pipeline with qdrant index <{self._qdrant_index}>..."
        )
        self.pipeline.warm_up()
        logger.info(
            f"Document writer pipeline warmed up successfully with qdrant index <{self._qdrant_index}>"
        )

    async def run(self, documents: List[Document]):
        """
        Running the document writer pipeline
        """
        logger.info(
            f"Running document writer pipeline with documents: <{','.join([item.content for item in documents])}>"
        )
        # documents = [Document(content=document) for document in documents]
        result = await asyncio.to_thread(
            self.pipeline.run,
            data={
                "embedder": {"documents": documents},
            },
        )

        logger.info(f"Document writer pipeline ran successfully.")

        return result
