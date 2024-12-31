import asyncio
from typing import List, Union
from haystack import Pipeline
from haystack.components.embedders import (
    SentenceTransformersTextEmbedder,
    SentenceTransformersDocumentEmbedder,
)
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from haystack.components.writers import DocumentWriter
from haystack.dataclasses import Document
from transformers import BertConfig
from rag_core.config import CONFIG
from rag_core.utils.logger import logger


class DocumentSearchPipeline:
    """进行文档的向量检索的管道"""

    def __init__(
        self,
        qdrant_index: str = "Document",
    ):
        self.qdrant_index = qdrant_index
        self._initialize_pipeline()
        self.warm_up()

    def __str__(self):
        return str(self.pipeline)

    def __repr__(self):
        return str(self.pipeline)

    def _initialize_pipeline(self):
        """初始化检索管道"""
        embedder = SentenceTransformersTextEmbedder(model=CONFIG.EMBEDDING_MODEL_PATH)
        retriever = QdrantEmbeddingRetriever(
            document_store=QdrantDocumentStore(
                host=CONFIG.QRANT_HOST,
                port=CONFIG.QRANT_PORT,
                embedding_dim=BertConfig.from_pretrained(
                    CONFIG.EMBEDDING_MODEL_PATH
                ).hidden_size,
                index=self.qdrant_index,
            )
        )
        self.pipeline = Pipeline()
        self.pipeline.add_component("embedder", embedder)
        self.pipeline.add_component("retriever", retriever)
        self.pipeline.connect("embedder.embedding", "retriever.query_embedding")

    def warm_up(self):
        """预热"""
        logger.info(f"预热文档检索管道中，索引：{self.qdrant_index}")
        self.pipeline.warm_up()
        logger.info(f"预热文档检索管道完成，索引：{self.qdrant_index}")

    async def run(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.7,
    ):
        """运行文档检索"""

        return await asyncio.to_thread(
            self.pipeline.run,
            {
                "embedder": {"text": query},
                "retriever": {"top_k": top_k, "score_threshold": score_threshold},
            },
        )


class DocumentWriterPipeline:
    """将文档写入到数据库中"""

    def __init__(
        self,
        qdrant_index: str,
    ):
        self.qdrant_index = qdrant_index
        self._initialize_pipeline()
        self.warm_up()

    def __str__(self):
        return str(self.pipeline)

    def __repr__(self):
        return str(self.pipeline)

    def _initialize_pipeline(self):
        """初始化检索管道"""
        document_store = QdrantDocumentStore(
            host=CONFIG.QRANT_HOST,
            port=CONFIG.QRANT_PORT,
            embedding_dim=BertConfig.from_pretrained(
                CONFIG.EMBEDDING_MODEL_PATH
            ).hidden_size,
            index=self.qdrant_index,
        )
        self.pipeline = Pipeline()
        self.pipeline.add_component(
            "embedder",
            SentenceTransformersDocumentEmbedder(model=CONFIG.EMBEDDING_MODEL_PATH),
        )
        self.pipeline.add_component(
            "writer", DocumentWriter(document_store=document_store)
        )
        self.pipeline.connect("embedder", "writer")

    def warm_up(self):
        """预热"""
        self.pipeline.warm_up()

    async def run(self, documents: Union[str, List[str]]):
        """运行文档写入"""
        if isinstance(documents, str):
            documents = [documents]
        documents = [Document(content=document) for document in documents]
        return self.pipeline.run(
            data={
                "embedder": {"documents": documents},
            }
        )
