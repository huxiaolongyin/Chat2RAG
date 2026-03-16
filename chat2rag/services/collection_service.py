import asyncio
import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from fastapi import UploadFile
from haystack.dataclasses import Document
from qdrant_client.http import models
from qdrant_client.models import FieldCondition, Filter, MatchValue

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
from chat2rag.parses.document_parser import (
    PDFParser,
    QAPairParser,
    TSVParser,
    WordParser,
)
from chat2rag.pipelines.document import DocumentSearchPipeline, DocumentWriterPipeline
from chat2rag.schemas.document import (
    CollectionData,
    DocumentData,
    ReindexResult,
    SourceLocation,
)
from chat2rag.services.contextual_retrieval import ContextualRetrieval
from chat2rag.utils.pipeline_cache import create_pipeline
from chat2rag.utils.qdrant_store import get_client

logger = get_logger(__name__)

_preview_cache: Dict[str, dict] = {}


class CollectionService:
    def __init__(self):
        self.client = get_client()

    async def create(self, collection_name: str):
        if await self.client.collection_exists(collection_name):
            raise ValueAlreadyExist(f"知识库<{collection_name}>已存在")
        return await self.client.create_collection(
            collection_name,
            vectors_config={
                "text-dense": models.VectorParams(
                    size=CONFIG.EMBEDDING_DIMENSIONS,
                    distance=models.Distance.COSINE,
                )
            },
            # vectors_config=VectorParams(size=CONFIG.EMBEDDING_DIMENSIONS, distance=Distance.COSINE),
            sparse_vectors_config={
                "text-sparse": models.SparseVectorParams(),
            },
        )

    async def remove(self, collection_name: str):
        if not await self.client.collection_exists(collection_name):
            raise ValueNoExist(f"知识库<{collection_name}>不存在")
        return await self.client.delete_collection(collection_name)

    async def reindex(
        self,
        collection_name: str,
        backup: bool = True,
    ) -> ReindexResult:
        """
        重新索引知识库

        适用于:
        - 向量名从 'default' 迁移到 'text-dense'
        - embedding 模型更换
        - 向量维度变化

        Args:
            collection_name: 知识库名称
            backup: 是否备份数据到文件

        Returns:
            ReindexResult: 重新索引结果
        """
        if not await self.client.collection_exists(collection_name):
            raise ValueNoExist(f"知识库<{collection_name}>不存在")

        logger.info(f"Starting reindex for collection: {collection_name}")

        backup_file = None
        points_count = 0

        points, _ = await self.client.scroll(
            collection_name=collection_name,
            limit=100000,
            with_payload=True,
            with_vectors=False,
        )
        points_count = len(points)
        logger.info(f"Exported {points_count} points from collection")

        if backup and points_count > 0:
            backup_file = await self._backup_points(collection_name, points)
            logger.info(f"Backup created: {backup_file}")

        await self.client.delete_collection(collection_name)
        logger.info(f"Deleted collection: {collection_name}")

        await self.create(collection_name)
        logger.info(f"Created new collection: {collection_name}")

        if points_count > 0:
            documents = []
            for point in points:
                payload = point.payload or {}
                content = payload.get("content", "")
                meta = payload.get("meta", {})

                documents.append(
                    Document(
                        id=str(point.id),
                        content=content,
                        meta=meta,
                    )
                )

            doc_write_pipeline = await create_pipeline(
                DocumentWriterPipeline, qdrant_index=collection_name
            )
            await doc_write_pipeline.run(documents)
            logger.info(f"Reindexed {points_count} documents")

        result = ReindexResult(
            points_count=points_count,
            backup_file=backup_file,
        )
        logger.info(f"Reindex completed: {result}")
        return result

    async def _backup_points(self, collection_name: str, points: list) -> str:
        backup_dir = CONFIG.DATA_DIR / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"{collection_name}_{timestamp}.json"

        backup_data = {
            "collection_name": collection_name,
            "backup_time": datetime.now().isoformat(),
            "points_count": len(points),
            "points": [
                {
                    "id": str(point.id),
                    "payload": point.payload,
                }
                for point in points
            ],
        }

        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)

        return str(backup_file)

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
            items = [
                item for item in items if collection_name.lower() in item.name.lower()
            ]

        total = len(items)

        # 获取详细信息
        for item in items:
            collection_info = await self.client.get_collection(item.name)
            vectors = collection_info.config.params.vectors
            if vectors is None:
                embedding_size = 0
                distance_str = ""
            elif isinstance(vectors, dict):
                first_vector = next(iter(vectors.values()))
                embedding_size = first_vector.size
                distance_str = str(first_vector.distance)
            else:
                embedding_size = vectors.size
                distance_str = str(vectors.distance)
            result.append(
                CollectionData(
                    collection_name=item.name,
                    status=collection_info.status,
                    documents_count=collection_info.points_count or 0,
                    embedding_size=embedding_size,
                    distance=distance_str,
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

    async def _filter_existing_documents(
        self, collection_name: str, doc_list: List[DocumentData]
    ):
        """过滤已存在的文档"""
        # 获取集合中所有的 points
        existing_points, _ = await self.client.scroll(
            collection_name=collection_name,
            limit=10000,
            with_payload=True,  # 根据实际调整
        )

        # 提取已存在的 content
        existing_contents = {
            point.payload.get("content") for point in existing_points if point.payload
        }

        # 过滤新文档，只保留不存在的
        filtered_list = [
            doc for doc in doc_list if doc.content not in existing_contents
        ]

        return filtered_list

    async def _write_document(self, collection_name: str, doc_list: List[DocumentData]):
        doc_write_pipeline = await create_pipeline(
            DocumentWriterPipeline, qdrant_index=collection_name
        )
        documents = [
            Document(
                id=doc.external_id or str(uuid.uuid4()),
                content=doc.content,
                meta=doc.model_dump(exclude={"content", "external_id"})
                | {"collection_name": collection_name},
            )
            for doc in doc_list
        ]
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
                        parent_doc_id=None,
                        chunk_index=None,
                        external_id=None,
                    ),
                    DocumentData(
                        doc_type=DocumentType.QA_PAIR,
                        content=f"{doc.question}:{doc.answer}",
                        answer=None,
                        source=SourceLocation(file_path="json"),
                        parent_doc_id=None,
                        chunk_index=None,
                        external_id=None,
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

    async def create(
        self,
        collection_name: str,
        file: UploadFile | None,
        preview: bool = False,
        max_chars: int = 600,
        overlap: int = 100,
    ) -> tuple[str | None, List[DocumentData] | None]:
        """
        通过文件创建知识点

        Returns:
            tuple: (cache_id, doc_list)
            - preview=True: 返回 (cache_id, doc_list)，缓存解析结果
            - preview=False: 返回 (None, None)，直接写入数据库
        """
        if not file or not file.filename:
            raise ValueError("文件名为空")
        filename = file.filename

        upload_dir = "uploads/documents"
        Path(upload_dir).mkdir(parents=True, exist_ok=True)

        name, ext = os.path.splitext(filename)
        timestamp = int(datetime.now().timestamp() * 1000)
        file_path = os.path.join(upload_dir, f"{name}_{timestamp}{ext}")

        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        context_generator = ContextualRetrieval()

        try:
            if filename.endswith((".csv", ".xlsx")):
                parser = QAPairParser()
                doc_list = await parser.parse(file_path)
            elif filename.endswith(".docx"):
                parser = WordParser(max_chars=max_chars, overlap=overlap)
                doc_list = await parser.parse_with_context(file_path, context_generator)
            elif filename.endswith(".pdf"):
                parser = PDFParser(max_chars=max_chars, overlap=overlap)
                doc_list = await parser.parse_with_context(file_path, context_generator)
            elif filename.endswith(".tsv"):
                parser = TSVParser()
                doc_list = await parser.parse(file_path)
            else:
                os.remove(file_path)
                msg = f"不支持的文件格式: {filename}"
                logger.warning(msg)
                raise ValueError(msg)
        except Exception as e:
            os.remove(file_path)
            logger.exception(f"文档解析失败: {e}")
            raise ValueError(f"文档解析失败: {str(e)}")

        if not doc_list:
            os.remove(file_path)
            msg = f"文件解析失败或为空: {filename}"
            logger.warning(msg)
            raise ValueError(msg)

        if preview:
            os.remove(file_path)
            cache_id = str(uuid.uuid4())
            _preview_cache[cache_id] = {
                "doc_list": doc_list,
                "file_path": file_path,
                "created_at": time.time(),
                "collection_name": collection_name,
            }
            return cache_id, doc_list

        doc_list = await self._filter_existing_documents(collection_name, doc_list)
        if not doc_list:
            msg = f"没有新知识点写入: {file_path}"
            logger.warning(msg)
            os.remove(file_path)
            raise ValueNoExist(msg)

        os.remove(file_path)
        return await self._write_document(collection_name, doc_list)

    async def create_from_cache(
        self,
        cache_id: str,
        collection_name: str,
    ) -> bool:
        """从缓存创建知识点"""
        if cache_id not in _preview_cache:
            raise ValueNoExist(f"缓存不存在或已过期: {cache_id}")

        cache_data = _preview_cache.pop(cache_id)
        doc_list = cache_data["doc_list"]

        doc_list = await self._filter_existing_documents(collection_name, doc_list)
        if not doc_list:
            msg = f"没有新知识点写入"
            logger.warning(msg)
            raise ValueNoExist(msg)

        return await self._write_document(collection_name, doc_list)

    async def remove(self, collection_name: str, doc_id_list: list):
        if not await self.client.collection_exists(collection_name):
            raise ValueNoExist(f"知识库<{collection_name}>不存在")

        # 如果是QA，需要把问题的文档ID也检索出来
        all_ids_to_delete = set(doc_id_list)

        # 获取要删除的文档信息
        documents = await self.client.retrieve(
            collection_name=collection_name, ids=doc_id_list
        )

        # 检查是否有QA_PAIR类型文档，找出关联的question文档
        for doc in documents:
            payload = doc.payload or {}
            if payload.get("meta", {}).get("doc_type") == DocumentType.QA_PAIR:
                qa_content = payload.get("content", "")
                if qa_content:
                    question = qa_content.split(":")[0]
                    answer = qa_content[len(question) + 1 :]
                    # 查询content等于answer且doc_type为question的文档
                    question_docs = await self.client.scroll(
                        collection_name=collection_name,
                        scroll_filter=Filter(
                            must=[
                                FieldCondition(
                                    key="meta.doc_type",
                                    match=MatchValue(value=DocumentType.QUESTION),
                                ),
                                FieldCondition(
                                    key="content", match=MatchValue(value=question)
                                ),
                                FieldCondition(
                                    key="meta.answer", match=MatchValue(value=answer)
                                ),
                            ]
                        ),
                        limit=100,
                    )
                    # 将找到的question文档ID加入删除列表
                    for question_doc in question_docs[0] or []:
                        all_ids_to_delete.add(question_doc.id)

        return await self.client.delete(
            collection_name=collection_name, points_selector=list(all_ids_to_delete)
        )

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
                must_not=[
                    FieldCondition(
                        key="meta.doc_type",
                        match=MatchValue(value=DocumentType.QUESTION),
                    )
                ]
            ),
            limit=10000,
            with_payload=True,  # 根据实际调整
        )

        if not document_list:
            return 0, []

        document_list = [
            {"id": doc.id, "content": (doc.payload or {}).get("content", "")}
            for doc in document_list
        ]

        # 内容过滤
        if document_content:
            document_list = [
                doc
                for doc in document_list
                if document_content.lower() in doc["content"].lower()
            ]

        # 排序
        document_list.sort(
            key=lambda x: x[sort_by], reverse=(sort_order == SortOrder.DESC)
        )

        # 计算分页
        total = len(document_list)
        start_index = (current - 1) * size
        end_index = start_index + size
        paginated_docs = document_list[start_index:end_index]

        return total, paginated_docs

    async def query(
        self,
        collection_name: str,
        query: str,
        top_k: int,
        score_threshold: float | None,
        doc_type: DocumentType,
    ) -> List[Document]:
        """检索知识点"""
        # 设置默认检索阈值
        if not score_threshold:
            score_threshold = (
                CONFIG.PRECISION_THRESHOLD
                if doc_type == DocumentType.QUESTION
                else CONFIG.SCORE_THRESHOLD
            )

        doc_search_pipeline = await create_pipeline(
            DocumentSearchPipeline, qdrant_index=collection_name
        )
        result = await doc_search_pipeline.run(
            query=query,
            top_k=top_k,
            score_threshold=score_threshold,
            filters={"field": "meta.doc_type", "operator": "==", "value": doc_type},
        )
        return result["retriever"]["documents"]

    async def query_exact(self, collection_name: str, query: str) -> Document | None:
        """通过匹配问题内容，精准检索知识点"""
        doc_search_pipeline = await create_pipeline(
            DocumentSearchPipeline, qdrant_index=collection_name
        )
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

    print(
        asyncio.run(
            document_service.query_exact("测试数据", "预约轮椅服务需要提前多久")
        )
    )
