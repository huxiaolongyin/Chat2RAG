import asyncio
from time import perf_counter
from typing import List, Optional, Tuple

from haystack.dataclasses import Document
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore

from rag_core.config.setting import CONFIG
from rag_core.dataclass.document import QADocument
from rag_core.logging import logger
from rag_core.pipelines.doc_pipeline import (
    DocumentSearchPipeline,
    DocumentWriterPipeline,
)


def prepare_documents(qa: QADocument) -> Tuple[Document, Document]:
    """
    将问题和答案装换为 Document
    """
    return (
        Document(
            content=qa.question, meta={"type": "question", "question_id": qa.question}
        ),
        Document(
            content=f"{qa.question}: {qa.answer}",
            meta={"type": "qa_pair", "question_id": qa.question},
        ),
    )


class QAQdrantDocumentStore(QdrantDocumentStore):
    """
    使用 Qdrant 进行问答库的文档管理，包含问题和答案的写入
    """

    def __init__(
        self,
        index: str = "Document",
        port: int = CONFIG.QDRANT_PORT,
        host: Optional[str] = CONFIG.QDRANT_HOST,
        grpc_port: int = CONFIG.QDRANT_GRPC_PORT,
        embedding_dim: int = CONFIG.EMBEDDING_DIMENSIONS,
    ):
        super().__init__(
            host=host,
            port=port,
            grpc_port=grpc_port,
            index=index,
            embedding_dim=embedding_dim,
        )

    @property
    def create(self):
        """
        创建一个集合
        """
        return self.client

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

    async def write_documents(
        self,
        qa_document_list: List[QADocument],
    ):
        """
        将 QADocument 内容写入 qdrant 数据库
        """
        documents = []
        for qa in qa_document_list:
            question_doc, answer_doc = prepare_documents(qa)
            documents.extend([question_doc, answer_doc])

        doc_write_pipeline = DocumentWriterPipeline(qdrant_index=self.index)
        return await doc_write_pipeline.run(documents=documents)

    @property
    def get_document_list(self) -> List[dict]:
        """
        进行文档的查询
        filter: 针对meta的过滤条件
        eg: {"field": "meta.type", "operator": "==", "value": "article"}
        """
        filters = {"field": "meta.type", "operator": "!=", "value": "question"}
        return [
            {"id": doc.id, "content": doc.content}
            for doc in self.filter_documents(filters)
        ]

    def delete_documents(self, doc_id_list: List[str]):
        """
        根据 id -> 对应 meta.question_id -> 删除
        """
        try:
            documents = super().get_documents_by_id(doc_id_list)
            question_id_list = [doc.meta.get("question_id") for doc in documents]
            filters = {
                "field": "meta.question_id",
                "operator": "in",
                "value": question_id_list,
            }
            doc_id_list = [doc.id for doc in self.filter_documents(filters)]
            return super().delete_documents(document_ids=doc_id_list)
        except Exception as e:
            logger.info("Only delete document without meta")
            return super().delete_documents(document_ids=doc_id_list)

    async def query(
        self,
        query: str,
        top_k: int = CONFIG.TOP_K,
        score_threshold: float = CONFIG.SCORE_THRESHOLD,
        type: str = "qa_pair",
    ) -> List[Document]:
        """
        进行 QA 全文的检索
        """
        start = perf_counter()
        doc_search_pipeline = DocumentSearchPipeline(self.index)
        response = await doc_search_pipeline.run(
            query=query,
            top_k=top_k,
            score_threshold=score_threshold,
            start=start,
            type=type,
        )
        documents = response.get("retriever").get("documents")
        # 优化 todo
        type_condition = lambda doc: (
            doc.meta.get("type") == type
            if type == "question"
            else doc.meta.get("type") != "question"
        )

        return [doc for doc in documents if type_condition(doc)]

    async def query_exact(self, query: str) -> Optional[str]:
        """
        通过精准匹配模式，直接索引问题，然后匹配答案
        """
        response = await self.query(
            query=query,
            score_threshold=CONFIG.PRECISION_THRESHOLD,
            top_k=1,
            type="question",
        )
        if not response:
            return None

        filters = {
            "operator": "AND",
            "conditions": [
                {
                    "field": "meta.question_id",
                    "operator": "==",
                    "value": response[0].content,
                },
                {
                    "field": "meta.type",
                    "operator": "==",
                    "value": "qa_pair",
                },
            ],
        }
        answer = self.filter_documents(filters=filters)
        if not answer:
            logger.warning(f"question: <{query}> and answer is not matched")
            return None
        return "".join(answer[0].content.split(": ")[1:])
