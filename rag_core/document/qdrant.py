import asyncio
from typing import List, Union

from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from transformers import BertConfig

from rag_core.config import CONFIG
from rag_core.pipelines.doc_pipeline import (
    DocumentSearchPipeline,
    DocumentWriterPipeline,
)
from rag_core.utils.logger import logger


class QdrantDocumentManage(QdrantDocumentStore):
    """Qdrant 文档的管理，包含文档的增删改查"""

    def __init__(
        self,
        index: str = "Document",
        host: str = CONFIG.QDRANT_HOST,
        port: int = CONFIG.QDRANT_PORT,
        grpc_port: int = CONFIG.QDRANT_GRPC_PORT,
    ):
        super().__init__(
            host=host,
            port=port,
            grpc_port=grpc_port,
            index=index,
            embedding_dim=BertConfig.from_pretrained(
                CONFIG.EMBEDDING_MODEL_PATH
            ).hidden_size,
        )

    @property
    def create(self):
        """
        创建一个集合
        """
        return self.client

    # self.client.create_collection(
    #         collection_name=self.index,
    #         vectors_config=VectorParams(
    #             size=self.embedding_dim,
    #             distance=Distance.COSINE,
    #         ),
    #     )

    @property
    def delete_collection(self):
        """
        删除一个集合
        """
        return self.client.delete_collection(collection_name=self.index)

    def get_collections(self):
        """
        Get all collections
        """
        logger.info("Get all collections...")
        collections = self.client.get_collections().model_dump()["collections"]
        result = []
        for collection in collections:
            collection_info = self.client.get_collection(collection["name"])
            result.append(
                {
                    "collection_name": collection["name"],
                    "status": collection_info.status.value,
                    "documents_count": collection_info.points_count,
                    "embedding_size": collection_info.config.params.vectors.size,
                    "distance": collection_info.config.params.vectors.distance.value,
                }
            )
        logger.info(f"Get all collections success")

        return result

    def get_collection_names(self):
        """
        获取所有集合名称
        """
        collections = self.client.get_collections().model_dump()["collections"]
        return [collection["name"] for collection in collections]

    async def write_documents(self, collection: str, documents: Union[str, List[str]]):
        """
        写入文档
        """
        try:
            doc_write_pipeline = DocumentWriterPipeline(qdrant_index=collection)
            result = await doc_write_pipeline.run(documents=documents)
        except Exception as e:
            raise RuntimeError(f"<def write_documents> failed: {str(e)}")

        return result

    @property
    def get_document_list(self, filter: dict = None) -> List[dict]:
        """查询文档
        filter: 针对meta的过滤条件
        eg: {"field": "meta.type", "operator": "==", "value": "article"}
        """
        return [
            {"id": doc.id, "content": doc.content}
            for doc in self.filter_documents(filter)
        ]

    async def query(self, query: str, top_k: int = 5, score_threshold: float = 0.5):
        """查询文档"""
        doc_search_pipeline = DocumentSearchPipeline(self.index)
        return await doc_search_pipeline.run(
            query=query, top_k=top_k, score_threshold=score_threshold
        )


async def main():
    qdrant = QdrantDocumentManage("人才集团")
    result = await qdrant.query("海外博士后项目支持政策有哪些")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
