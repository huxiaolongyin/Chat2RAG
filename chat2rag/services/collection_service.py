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
    FileStatus,
    FileType,
    SortOrder,
)
from chat2rag.core.exceptions import ValueAlreadyExist, ValueNoExist
from chat2rag.core.logger import get_logger
from chat2rag.dataclass.document import QADocument
from chat2rag.models import File
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
from chat2rag.utils.qdrant_store import detect_vector_mode, get_client

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
        )

    async def remove(self, collection_name: str):
        if not await self.client.collection_exists(collection_name):
            raise ValueNoExist(f"知识库<{collection_name}>不存在")
        return await self.client.delete_collection(collection_name)

    async def reindex(
        self,
        collection_name: str,
        backup: bool = True,
        sync_files: bool = True,
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
            sync_files: 是否同步文件信息到关系型数据库

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

        file_id_map = {}
        if sync_files and points_count > 0:
            file_id_map = await self._sync_files_from_points(collection_name, points)
            logger.info(f"Synced {len(file_id_map)} files to database")

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

                if sync_files and file_id_map:
                    source = meta.get("source", {})
                    file_path = source.get("file_path", "") if isinstance(source, dict) else ""
                    if file_path and file_path in file_id_map:
                        meta = {**meta, "file_id": file_id_map[file_path]}

                documents.append(
                    Document(
                        id=str(point.id),
                        content=content,
                        meta=meta | {"collection_name": collection_name},
                    )
                )

            doc_write_pipeline = await create_pipeline(DocumentWriterPipeline, qdrant_index=collection_name)
            await doc_write_pipeline.run(documents)
            logger.info(f"Reindexed {points_count} documents")

        result = ReindexResult(
            points_count=points_count,
            backup_file=backup_file,
            synced_files_count=len(file_id_map),
        )
        logger.info(f"Reindex completed: {result}")
        return result

    async def _sync_files_from_points(self, collection_name: str, points: list) -> Dict[str, int]:
        """
        从知识点中提取文件信息，同步到关系型数据库

        Returns:
            Dict[str, int]: file_path -> file_id 的映射
        """
        file_info_map: Dict[str, dict] = {}

        for point in points:
            payload = point.payload or {}
            meta = payload.get("meta", {})
            source = meta.get("source", {})

            if not isinstance(source, dict):
                continue

            file_path = source.get("file_path", "")
            if not file_path or file_path == "json":
                continue

            if file_path not in file_info_map:
                file_info_map[file_path] = {
                    "chunk_count": 0,
                    "doc_types": set(),
                    "is_qa_file": False,
                }
            file_info_map[file_path]["chunk_count"] += 1
            doc_type = meta.get("doc_type")
            if doc_type:
                file_info_map[file_path]["doc_types"].add(doc_type)
                if doc_type == DocumentType.QUESTION:
                    file_info_map[file_path]["is_qa_file"] = True

        file_id_map = {}
        for file_path, info in file_info_map.items():
            existing_file = await File.get_or_none(collection_name=collection_name, file_path=file_path)
            if existing_file:
                file_id_map[file_path] = existing_file.id
                continue

            filename = os.path.basename(file_path)
            ext = os.path.splitext(filename)[1].lower()
            type_map = {
                ".pdf": FileType.PDF,
                ".docx": FileType.DOCX,
                ".xlsx": FileType.XLSX,
                ".xls": FileType.XLS,
                ".csv": FileType.CSV,
                ".tsv": FileType.TSV,
                ".json": FileType.JSON,
            }
            file_type = type_map.get(ext, FileType.UNKNOWN)

            file_size = 0
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)

            actual_chunk_count = info["chunk_count"] // 2 if info.get("is_qa_file") else info["chunk_count"]
            db_file = await File.create(
                collection_name=collection_name,
                filename=filename,
                file_type=file_type,
                file_size=file_size,
                file_path=file_path,
                status=FileStatus.PARSED,
                chunk_count=actual_chunk_count,
            )
            file_id_map[file_path] = db_file.id
            logger.info(f"Created file record: {filename} (id={db_file.id})")

        return file_id_map

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
        items = [item for item in items if item.name not in ["Document", "questions", "eval", "None"]]

        # 按 collection_name 过滤
        if collection_name:
            items = [item for item in items if collection_name.lower() in item.name.lower()]

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
            files_count = await File.filter(collection_name=item.name).count()
            vector_mode = await detect_vector_mode(self.client, item.name)
            # 统计 doc_type != 'question' 的文档数量
            count_result = await self.client.count(
                collection_name=item.name,
                count_filter=Filter(
                    must_not=[
                        FieldCondition(
                            key="meta.doc_type",
                            match=MatchValue(value=DocumentType.QUESTION),
                        )
                    ]
                ),
            )
            documents_count = count_result.count
            result.append(
                CollectionData(
                    collection_name=item.name,
                    status=collection_info.status,
                    documents_count=documents_count,
                    files_count=files_count,
                    embedding_size=embedding_size,
                    distance=distance_str,
                    vector_mode=vector_mode,
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

    def _convert_source_to_camel_case(self, source: dict | None) -> dict | None:
        if not source:
            return source
        return {
            "filePath": source.get("file_path"),
            "pageNum": source.get("page_num"),
            "section": source.get("section"),
            "paragraphNum": source.get("paragraph_num"),
            "lineNum": source.get("line_num"),
            "tableName": source.get("table_name"),
            "url": source.get("url"),
        }

    async def _filter_existing_documents(self, collection_name: str, doc_list: List[DocumentData]):
        """过滤已存在的文档"""
        # 获取集合中所有的 points
        existing_points, _ = await self.client.scroll(
            collection_name=collection_name,
            limit=10000,
            with_payload=True,  # 根据实际调整
        )

        # 提取已存在的 content
        existing_contents = {point.payload.get("content") for point in existing_points if point.payload}

        # 过滤新文档，只保留不存在的
        filtered_list = [doc for doc in doc_list if doc.content not in existing_contents]

        return filtered_list

    async def _write_document(self, collection_name: str, doc_list: List[DocumentData]):
        doc_write_pipeline = await create_pipeline(DocumentWriterPipeline, qdrant_index=collection_name)
        documents = [
            Document(
                id=doc.external_id or str(uuid.uuid4()),
                content=doc.content,
                meta=doc.model_dump(exclude={"content", "external_id"}) | {"collection_name": collection_name},
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
        [已废弃] 通过文件创建知识点

        请使用 file_service.create 方法代替

        Returns:
            tuple: (cache_id, doc_list)
            - preview=True: 返回 (cache_id, doc_list)，缓存解析结果
            - preview=False: 返回 (None, None)，直接写入数据库
        """
        import warnings

        warnings.warn(
            "DocumentService.create 已废弃，请使用 file_service.create",
            DeprecationWarning,
            stacklevel=2,
        )
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
        """
        [已废弃] 从缓存创建知识点

        请使用 file_service.create 方法代替
        """
        import warnings

        warnings.warn(
            "DocumentService.create_from_cache 已废弃",
            DeprecationWarning,
            stacklevel=2,
        )
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
        documents = await self.client.retrieve(collection_name=collection_name, ids=doc_id_list)

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
                                FieldCondition(key="content", match=MatchValue(value=question)),
                                FieldCondition(key="meta.answer", match=MatchValue(value=answer)),
                            ]
                        ),
                        limit=100,
                    )
                    # 将找到的question文档ID加入删除列表
                    for question_doc in question_docs[0] or []:
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
        file_id: int | None = None,
        file_path: str | None = None,
    ):
        must_not_conditions = [
            FieldCondition(
                key="meta.doc_type",
                match=MatchValue(value=DocumentType.QUESTION),
            )
        ]

        must_conditions = []
        if file_id == -1:
            must_conditions.append(
                Filter(
                    must=[
                        FieldCondition(
                            key="meta.source.file_path",
                            match=MatchValue(value="json"),
                        )
                    ]
                )
            )
        elif file_id is not None:
            must_conditions.append(FieldCondition(key="meta.file_id", match=MatchValue(value=file_id)))
        elif file_path is not None:
            must_conditions.append(FieldCondition(key="meta.source.file_path", match=MatchValue(value=file_path)))

        scroll_filter = (
            Filter(must_not=must_not_conditions, must=must_conditions)
            if must_conditions
            else Filter(must_not=must_not_conditions)
        )

        document_list, _ = await self.client.scroll(
            collection_name=collection_name,
            scroll_filter=scroll_filter,
            limit=10000,
            with_payload=True,
        )

        if not document_list:
            return 0, []

        document_list = [
            {
                "id": str(doc.id),
                "content": (doc.payload or {}).get("content", ""),
                "docType": (doc.payload or {}).get("meta", {}).get("doc_type"),
                "fileId": (doc.payload or {}).get("meta", {}).get("file_id"),
                "source": self._convert_source_to_camel_case((doc.payload or {}).get("meta", {}).get("source")),
                "chunkIndex": (doc.payload or {}).get("meta", {}).get("chunk_index"),
            }
            for doc in document_list
        ]

        if document_content:
            document_list = [doc for doc in document_list if document_content.lower() in doc["content"].lower()]

        document_list.sort(key=lambda x: x[sort_by], reverse=(sort_order == SortOrder.DESC))

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
                CONFIG.PRECISION_THRESHOLD if doc_type == DocumentType.QUESTION else CONFIG.SCORE_THRESHOLD
            )

        doc_search_pipeline = await create_pipeline(DocumentSearchPipeline, qdrant_index=collection_name)
        result = await doc_search_pipeline.run(
            query=query,
            top_k=top_k,
            score_threshold=score_threshold,
            filters={"field": "meta.doc_type", "operator": "==", "value": doc_type},
        )
        output_key = "ranker" if CONFIG.RERANK_ENABLED else "retriever"
        return result[output_key]["documents"]

    async def query_exact(self, collection_name: str, query: str) -> Document | None:
        """通过匹配问题内容，精准检索知识点"""
        doc_search_pipeline = await create_pipeline(DocumentSearchPipeline, qdrant_index=collection_name)
        result = await doc_search_pipeline.run(
            query=query,
            top_k=1,
            score_threshold=CONFIG.PRECISION_THRESHOLD,
            filters={"field": "meta.doc_type", "operator": "==", "value": "question"},
        )

        output_key = "ranker" if CONFIG.RERANK_ENABLED else "retriever"
        return next(iter(result[output_key]["documents"]), None)


collection_service = CollectionService()
document_service = DocumentService()

if __name__ == "__main__":
    import asyncio

    print(asyncio.run(document_service.query_exact("测试数据", "预约轮椅服务需要提前多久")))
