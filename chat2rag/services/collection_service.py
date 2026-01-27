import os
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import UploadFile
from haystack.dataclasses import Document
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    VectorParams,
)

from chat2rag.config import CONFIG
from chat2rag.core.enums import (
    CollectionSortField,
    DocumentSortField,
    DocumentType,
    SortOrder,
)
from chat2rag.core.exceptions import ValueAlreadyExist, ValueNoExist
from chat2rag.core.logger import get_logger
from chat2rag.dataclass.document import QADocument
from chat2rag.parses.document_parser import PDFParser, QAPairParser
from chat2rag.pipelines.document import DocumentSearchPipeline, DocumentWriterPipeline
from chat2rag.schemas.document import CollectionData, DocumentData, SourceLocation
from chat2rag.utils.pipeline_cache import create_pipeline
from chat2rag.utils.qdrant_store import get_client

logger = get_logger(__name__)


class CollectionService:
    def __init__(self):
        self.client = get_client()

    async def create(self, collection_name: str):
        if await self.client.collection_exists(collection_name):
            raise ValueAlreadyExist(f"知识库<{collection_name}>已存在")
        return await self.client.create_collection(
            collection_name, vectors_config=VectorParams(size=CONFIG.EMBEDDING_DIMENSIONS, distance=Distance.COSINE)
        )

    async def remove(self, collection_name: str):
        if not await self.client.collection_exists(collection_name):
            raise ValueNoExist(f"知识库<{collection_name}>不存在")
        return await self.client.delete_collection(collection_name)

    async def get_list(
        self,
        current: int,
        size: int,
        sort_by: CollectionSortField,
        sort_order: SortOrder,
        collection_name: str | None = None,
    ):
        result = []
        collections_summary = await self.client.get_collections()
        items = collections_summary.collections

        # 去除内置使用库
        items = [item for item in items if item.name not in ["Document", "questions"]]

        # 按 collection_name 过滤
        if collection_name:
            items = [item for item in items if collection_name.lower() in item.name.lower()]

        total = len(items)

        # 获取详细信息
        for item in items:
            collection_info = await self.client.get_collection(item.name)
            result.append(
                CollectionData(
                    collection_name=item.name,
                    status=collection_info.status,
                    documents_count=collection_info.points_count,
                    embedding_size=collection_info.config.params.vectors.size,
                    distance=collection_info.config.params.vectors.distance,
                )
            )
        # 排序
        sort_key_map = {
            CollectionSortField.COLLECTION_NAME: lambda x: x.collection_name,
            CollectionSortField.DOCUMENT_COUNT: lambda x: x.documents_count,
        }
        sort_key = sort_key_map.get(sort_by, lambda x: x.collection_name)
        reverse = sort_order == SortOrder.DESC
        result.sort(key=sort_key, reverse=reverse)

        # 分页
        start = (current - 1) * size
        end = start + size

        return total, result[start:end]


class DocumentService:
    def __init__(self):
        self.client = get_client()

    async def _filter_existing_documents(self, collection_name: str, doc_list: List[DocumentData]):
        """过滤已存在的文档"""
        # 获取集合中所有的 points
        existing_points, _ = await self.client.scroll(
            collection_name=collection_name, limit=10000, with_payload=True  # 根据实际调整
        )

        # 提取已存在的 content
        existing_contents = {point.payload.get("content") for point in existing_points}

        # 过滤新文档，只保留不存在的
        filtered_list = [doc for doc in doc_list if doc.content not in existing_contents]

        return filtered_list

    async def _write_document(self, collection_name: str, doc_list: List[DocumentData]):
        """文档写入"""
        doc_write_pipeline = await create_pipeline(DocumentWriterPipeline, qdrant_index=collection_name)
        documents = [Document(content=doc.content, meta=doc.model_dump(exclude=["content"])) for doc in doc_list]
        return await doc_write_pipeline.run(documents)

    async def create_by_json(self, collection_name: str, documents: List[QADocument]):
        doc_list = []
        for doc in documents:
            doc_list.extend(
                [
                    DocumentData(
                        doc_type=DocumentType.QUESTION,
                        content=doc.question,
                        answer=doc.answer,
                        source=SourceLocation(file_path="json"),
                    ),
                    DocumentData(
                        doc_type=DocumentType.QA_PAIR,
                        content=f"{doc.question}:{doc.answer}",
                        source=SourceLocation(file_path="json"),
                    ),
                ]
            )

        # 比对已有知识内容，保留没有的知识点
        doc_list = await self._filter_existing_documents(collection_name, doc_list)

        if not doc_list:
            msg = f"没有新知识点写入"
            logger.warning(msg)
            raise ValueNoExist(msg)

        return await self._write_document(collection_name, doc_list)

    async def create(self, collection_name: str, file: UploadFile):
        """通过文件 创建知识点"""

        # 创建目录（如果不存在）
        upload_dir = "uploads/documents"
        Path(upload_dir).mkdir(parents=True, exist_ok=True)

        # 保存上传的文件
        name, ext = os.path.splitext(file.filename)
        timestamp = int(datetime.now().timestamp() * 1000)  # 毫秒级
        file_path = os.path.join(upload_dir, f"{name}_{timestamp}{ext}")

        # 读取并保存文件
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        """处理各个格式的文件成 DocumentData"""
        if file.filename.endswith((".csv", ".xlsx")):
            parser = QAPairParser()
            doc_list = await parser.parse(file_path)
        elif file.filename.endswith(".pdf"):
            parser = PDFParser()
            doc_list = await parser.parse(file_path)
        else:
            msg = f"不支持的文件格式: {file_path}"
            logger.warning(msg)
            raise ValueError(msg)

        # 验证是否成功解析
        if not doc_list:
            msg = f"文件解析失败或为空: {file_path}"
            logger.warning(msg)
            raise ValueError(msg)

        # 比对已有知识内容，保留没有的知识点
        doc_list = await self._filter_existing_documents(collection_name, doc_list)
        if not doc_list:
            msg = f"没有新知识点写入: {file_path}"
            logger.warning(msg)
            # 删除文件
            os.remove(file_path)
            raise ValueNoExist(msg)

        return await self._write_document(collection_name, doc_list)

    async def remove(self, collection_name: str, doc_id_list: list):
        if not await self.client.collection_exists(collection_name):
            raise ValueNoExist(f"知识库<{collection_name}>不存在")

        # 如果是QA，需要把问题的文档ID也检索出来
        all_ids_to_delete = set(doc_id_list)

        # 获取要删除的文档信息
        documents = await self.client.retrieve(collection_name=collection_name, ids=doc_id_list)

        # 检查是否有QA_PAIR类型文档，找出关联的question文档
        for doc in documents:
            if doc.payload.get("meta", {}).get("doc_type") == DocumentType.QA_PAIR:
                qa_content = doc.payload.get("content", "")
                if qa_content:
                    question, answer = qa_content.split(":")
                    # 查询content等于answer且doc_type为question的文档
                    question_docs = await self.client.scroll(
                        collection_name=collection_name,
                        scroll_filter=Filter(
                            must=[
                                FieldCondition(key="meta.doc_type", match=MatchValue(value=DocumentType.QUESTION)),
                                FieldCondition(key="content", match=MatchValue(value=question)),
                                FieldCondition(key="meta.answer", match=MatchValue(value=answer)),
                            ]
                        ),
                        limit=100,
                    )
                    # 将找到的question文档ID加入删除列表
                    for question_doc in question_docs[0]:
                        all_ids_to_delete.add(question_doc.id)

        return await self.client.delete(collection_name=collection_name, points_selector=list(all_ids_to_delete))

    async def get_list(
        self,
        collection_name: str,
        current: int,
        size: int,
        sort_by: DocumentSortField,
        sort_order: SortOrder,
        document_content: str | None,
    ):
        document_list, _ = await self.client.scroll(
            collection_name=collection_name,
            scroll_filter=Filter(
                must_not=[FieldCondition(key="meta.doc_type", match=MatchValue(value=DocumentType.QUESTION))]
            ),
            limit=10000,
            with_payload=True,  # 根据实际调整
        )

        if not document_list:
            return 0, []

        document_list = [{"id": doc.id, "content": doc.payload["content"]} for doc in document_list]

        # 内容过滤
        if document_content:
            document_list = [doc for doc in document_list if document_content.lower() in doc["content"].lower()]

        # 排序
        document_list.sort(key=lambda x: x[sort_by], reverse=(sort_order == SortOrder.DESC))

        # 计算分页
        total = len(document_list)
        start_index = (current - 1) * size
        end_index = start_index + size
        paginated_docs = document_list[start_index:end_index]

        return total, paginated_docs

    async def query(
        self, collection_name: str, query: str, top_k: int, score_threshold: float | None, doc_type: DocumentType
    ) -> List[Document]:
        """检索知识点"""
        # 设置默认检索阈值
        if not score_threshold:
            score_threshold = (
                CONFIG.PRECISION_THRESHOLD if doc_type == DocumentType.QUESTION else CONFIG.SCORE_THRESHOLD
            )

        doc_search_pipeline = await create_pipeline(DocumentSearchPipeline, qdrant_index=collection_name)
        result = await doc_search_pipeline.run(
            query=query,
            top_k=top_k,
            score_threshold=score_threshold,
            filters={"field": "meta.doc_type", "operator": "==", "value": doc_type},
        )
        return result["retriever"]["documents"]

    async def query_exact(self, collection_name: str, query: str) -> Document | None:
        """通过匹配问题内容，精准检索知识点"""
        doc_search_pipeline = await create_pipeline(DocumentSearchPipeline, qdrant_index=collection_name)
        result = await doc_search_pipeline.run(
            query=query,
            top_k=1,
            score_threshold=CONFIG.PRECISION_THRESHOLD,
            filters={"field": "meta.doc_type", "operator": "==", "value": "question"},
        )

        return next(iter(result["retriever"]["documents"]), None)


collection_service = CollectionService()
document_service = DocumentService()

if __name__ == "__main__":
    import asyncio

    print(asyncio.run(document_service.query_exact("测试数据", "预约轮椅服务需要提前多久")))
