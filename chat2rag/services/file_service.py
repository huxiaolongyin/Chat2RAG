import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import UploadFile
from haystack.dataclasses import Document
from qdrant_client.http import models
from qdrant_client.models import FieldCondition, Filter, MatchValue

from chat2rag.config import CONFIG
from chat2rag.core.enums import FileStatus, FileType
from chat2rag.core.exceptions import ValueNoExist
from chat2rag.core.logger import get_logger
from chat2rag.models import File, FileVersion
from chat2rag.parses.document_parser import (
    PDFParser,
    QAPairParser,
    TSVParser,
    WordParser,
)
from chat2rag.pipelines.document import DocumentWriterPipeline
from chat2rag.schemas.document import DocumentData, SourceLocation
from chat2rag.services.collection_service import collection_service
from chat2rag.services.contextual_retrieval import ContextualRetrieval
from chat2rag.utils.pipeline_cache import create_pipeline
from chat2rag.utils.preview_cache import preview_cache
from chat2rag.utils.qdrant_store import get_client

logger = get_logger(__name__)

UPLOAD_DIR = Path("uploads/files")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_file_type(filename: str) -> FileType:
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
    return type_map.get(ext, FileType.UNKNOWN)


class FileService:
    def __init__(self):
        self.client = get_client()

    async def get_list(
        self,
        collection_name: str,
        current: int = 1,
        size: int = 20,
        filename: Optional[str] = None,
        status: Optional[FileStatus] = None,
    ) -> tuple[int, List[File]]:
        query = File.filter(collection_name=collection_name)

        if filename:
            query = query.filter(filename__icontains=filename)
        if status:
            query = query.filter(status=status)

        db_total = await query.count()
        db_files = (
            await query.order_by("-create_time")
            .offset((current - 1) * size)
            .limit(size)
        )

        json_file = await self._get_json_file_data(collection_name)
        if not json_file:
            return db_total, db_files

        if filename and "json" not in filename.lower() and "导入" not in filename:
            return db_total, db_files
        if status and status != FileStatus.PARSED:
            return db_total, db_files

        total = db_total + 1
        json_file_obj = self._create_json_file_model(json_file, collection_name)

        if current == 1:
            return total, [json_file_obj] + db_files[: size - 1]
        else:
            start = (current - 1) * size - 1
            if start < 0:
                return total, db_files
            return total, db_files

    async def get_by_id(self, file_id: int) -> Optional[File]:
        if file_id == -1:
            return None
        obj = await File.get_or_none(id=file_id)
        if obj:
            await obj.fetch_related("versions")
        return obj

    async def _get_json_file_data(self, collection_name: str) -> dict | None:
        from chat2rag.core.enums import DocumentType

        chunks, _ = await self.client.scroll(
            collection_name=collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="meta.source.file_path",
                        match=MatchValue(value="json"),
                    ),
                    FieldCondition(
                        key="meta.doc_type",
                        match=MatchValue(value=DocumentType.QUESTION),
                    ),
                ]
            ),
            limit=10000,
            with_payload=False,
        )
        chunk_count = len(chunks)
        if chunk_count == 0:
            return None
        return {"chunk_count": chunk_count}

    def _create_json_file_model(self, json_data: dict, collection_name: str) -> File:
        json_file = File(
            id=-1,
            collection_name=collection_name,
            filename="JSON导入",
            file_type=FileType.JSON,
            file_size=0,
            file_path="json",
            status=FileStatus.PARSED,
            version=1,
            chunk_count=json_data["chunk_count"],
        )
        return json_file

    async def create(
        self,
        collection_name: str,
        file: UploadFile,
        max_chars: int = 600,
        overlap: int = 100,
        preview: bool = False,
        preview_id: str | None = None,
    ) -> tuple[File, List[DocumentData] | None]:
        if not file or not file.filename:
            raise ValueError("文件名为空")

        filename = file.filename
        file_type = get_file_type(filename)
        content = await file.read()
        file_size = len(content)

        file_path = self._save_file(content, filename, collection_name)

        db_file = await File.create(
            collection_name=collection_name,
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            file_path=file_path,
            status=FileStatus.PARSING,
            parse_config={"maxChars": max_chars, "overlap": overlap},
        )

        try:
            doc_list = None
            if preview_id:
                doc_list = await preview_cache.get(
                    preview_id, content, max_chars, overlap
                )

            if doc_list is None:
                doc_list = await self._parse_file(
                    file_path, file_type, max_chars, overlap
                )
            else:
                logger.info(f"使用预览缓存，跳过大模型处理: preview_id={preview_id}")

            if preview:
                return db_file, doc_list

            await self._write_documents(collection_name, db_file.id, doc_list)

            actual_chunk_count = (
                len(doc_list) // 2
                if file_type in (FileType.XLSX, FileType.XLS, FileType.CSV)
                else len(doc_list)
            )
            db_file.status = FileStatus.PARSED
            db_file.chunk_count = actual_chunk_count
            await db_file.save()

            await FileVersion.create(
                file_id=db_file.id,
                version=1,
                file_path=file_path,
                file_size=file_size,
                chunk_count=actual_chunk_count,
                parse_config={"maxChars": max_chars, "overlap": overlap},
            )

            return db_file, None

        except Exception as e:
            db_file.status = FileStatus.FAILED
            db_file.error_message = str(e)
            await db_file.save()
            raise

    async def create_version(
        self,
        file_id: int,
        file: UploadFile,
        change_note: Optional[str] = None,
        max_chars: int = 600,
        overlap: int = 100,
    ) -> File:
        db_file = await self.get_by_id(file_id)
        if not db_file:
            raise ValueNoExist(f"文件不存在: {file_id}")

        content = await file.read()
        file_size = len(content)
        if not file.filename:
            raise ValueError("文件名为空")
        new_file_path = self._save_file(content, file.filename, db_file.collection_name)

        old_chunks = await self._get_file_chunks(db_file.collection_name, file_id)
        if old_chunks:
            await self.client.delete(
                collection_name=db_file.collection_name,
                points_selector=[doc.id for doc in old_chunks],
            )

        try:
            doc_list = await self._parse_file(
                new_file_path, db_file.file_type, max_chars, overlap
            )
            await self._write_documents(db_file.collection_name, file_id, doc_list)

            actual_chunk_count = (
                len(doc_list) // 2
                if db_file.file_type in (FileType.XLSX, FileType.XLS, FileType.CSV)
                else len(doc_list)
            )
            new_version = db_file.version + 1
            await FileVersion.create(
                file_id=file_id,
                version=new_version,
                file_path=new_file_path,
                file_size=file_size,
                change_note=change_note,
                chunk_count=actual_chunk_count,
                parse_config={"maxChars": max_chars, "overlap": overlap},
            )

            db_file.file_path = new_file_path
            db_file.file_size = file_size
            db_file.version = new_version
            db_file.chunk_count = actual_chunk_count
            db_file.parse_config = {"maxChars": max_chars, "overlap": overlap}
            db_file.status = FileStatus.PARSED
            await db_file.save()

            return db_file

        except Exception as e:
            db_file.status = FileStatus.FAILED
            db_file.error_message = str(e)
            await db_file.save()
            raise

    async def get_versions(self, file_id: int) -> List[FileVersion]:
        return await FileVersion.filter(file_id=file_id).order_by("-version")

    async def rollback(self, file_id: int, version: int) -> File:
        db_file = await self.get_by_id(file_id)
        if not db_file:
            raise ValueNoExist(f"文件不存在: {file_id}")

        target_version = await FileVersion.get_or_none(file_id=file_id, version=version)
        if not target_version:
            raise ValueNoExist(f"版本不存在: {version}")

        old_chunks = await self._get_file_chunks(db_file.collection_name, file_id)
        if old_chunks:
            await self.client.delete(
                collection_name=db_file.collection_name,
                points_selector=[doc.id for doc in old_chunks],
            )

        parse_config = target_version.parse_config or {}
        doc_list = await self._parse_file(
            target_version.file_path,
            db_file.file_type,
            parse_config.get("maxChars", 600),
            parse_config.get("overlap", 100),
        )

        await self._write_documents(db_file.collection_name, file_id, doc_list)

        actual_chunk_count = (
            len(doc_list) // 2
            if db_file.file_type in (FileType.XLSX, FileType.XLS, FileType.CSV)
            else len(doc_list)
        )
        db_file.version = target_version.version
        db_file.chunk_count = actual_chunk_count
        db_file.status = FileStatus.PARSED
        await db_file.save()

        return db_file

    async def reparse(
        self,
        file_id: int,
        max_chars: int = 600,
        overlap: int = 100,
    ) -> File:
        db_file = await self.get_by_id(file_id)
        if not db_file:
            raise ValueNoExist(f"文件不存在: {file_id}")

        if not db_file.file_path or not os.path.exists(db_file.file_path):
            raise ValueNoExist(f"文件不存在: {db_file.file_path}")

        old_chunks = await self._get_file_chunks(db_file.collection_name, file_id)
        if old_chunks:
            await self.client.delete(
                collection_name=db_file.collection_name,
                points_selector=[doc.id for doc in old_chunks],
            )

        try:
            doc_list = await self._parse_file(
                db_file.file_path, db_file.file_type, max_chars, overlap
            )
            await self._write_documents(db_file.collection_name, file_id, doc_list)

            actual_chunk_count = (
                len(doc_list) // 2
                if db_file.file_type in (FileType.XLSX, FileType.XLS, FileType.CSV)
                else len(doc_list)
            )
            new_version = db_file.version + 1
            await FileVersion.create(
                file_id=file_id,
                version=new_version,
                file_path=db_file.file_path,
                file_size=db_file.file_size,
                change_note="重新解析",
                chunk_count=actual_chunk_count,
                parse_config={"maxChars": max_chars, "overlap": overlap},
            )

            db_file.version = new_version
            db_file.chunk_count = actual_chunk_count
            db_file.parse_config = {"maxChars": max_chars, "overlap": overlap}
            db_file.status = FileStatus.PARSED
            await db_file.save()

            return db_file

        except Exception as e:
            db_file.status = FileStatus.FAILED
            db_file.error_message = str(e)
            await db_file.save()
            raise

    async def delete(self, file_id: int) -> bool:
        if file_id == -1:
            raise ValueNoExist("JSON导入数据不支持删除，请通过文档管理接口删除")

        db_file = await self.get_by_id(file_id)
        if not db_file:
            raise ValueNoExist(f"文件不存在: {file_id}")

        chunks = await self._get_file_chunks(db_file.collection_name, file_id)
        if chunks:
            await self.client.delete(
                collection_name=db_file.collection_name,
                points_selector=[doc.id for doc in chunks],
            )

        if db_file.file_path and os.path.exists(db_file.file_path):
            os.remove(db_file.file_path)

        await FileVersion.filter(file_id=file_id).delete()
        await db_file.delete()

        return True

    async def get_chunks(
        self,
        collection_name: str,
        file_id: int,
        current: int = 1,
        size: int = 20,
    ) -> tuple[int, List[dict]]:
        if file_id == -1:
            scroll_filter = Filter(
                must=[
                    FieldCondition(
                        key="meta.source.file_path",
                        match=MatchValue(value="json"),
                    )
                ]
            )
        else:
            scroll_filter = Filter(
                must=[
                    FieldCondition(
                        key="meta.file_id",
                        match=MatchValue(value=file_id),
                    )
                ]
            )

        chunks, _ = await self.client.scroll(
            collection_name=collection_name,
            scroll_filter=scroll_filter,
            limit=10000,
            with_payload=True,
        )

        if not chunks:
            return 0, []

        chunk_list = [
            {
                "id": str(chunk.id),
                "content": (chunk.payload or {}).get("content", ""),
                "chunkIndex": (chunk.payload or {}).get("meta", {}).get("chunk_index"),
            }
            for chunk in chunks
        ]

        total = len(chunk_list)
        start = (current - 1) * size
        end = start + size

        return total, chunk_list[start:end]

    def _save_file(self, content: bytes, filename: str, collection_name: str) -> str:
        collection_dir = UPLOAD_DIR / collection_name
        collection_dir.mkdir(parents=True, exist_ok=True)

        name, ext = os.path.splitext(filename)
        timestamp = int(datetime.now().timestamp() * 1000)
        unique_name = f"{name}_{timestamp}{ext}"

        file_path = collection_dir / unique_name
        with open(file_path, "wb") as f:
            f.write(content)

        return str(file_path)

    async def _parse_file(
        self,
        file_path: str,
        file_type: FileType,
        max_chars: int,
        overlap: int,
    ) -> List[DocumentData]:
        context_generator = ContextualRetrieval()

        if file_type == FileType.PDF:
            parser = PDFParser(max_chars=max_chars, overlap=overlap)
            return await parser.parse_with_context(file_path, context_generator)
        elif file_type == FileType.DOCX:
            parser = WordParser(max_chars=max_chars, overlap=overlap)
            return await parser.parse_with_context(file_path, context_generator)
        elif file_type in (FileType.XLSX, FileType.XLS, FileType.CSV):
            parser = QAPairParser()
            return await parser.parse(file_path)
        elif file_type == FileType.TSV:
            parser = TSVParser()
            return await parser.parse(file_path)
        else:
            raise ValueError(f"不支持的文件类型: {file_type}")

    async def _write_documents(
        self,
        collection_name: str,
        file_id: int,
        doc_list: List[DocumentData],
    ):
        doc_write_pipeline = await create_pipeline(
            DocumentWriterPipeline, qdrant_index=collection_name
        )
        documents = [
            Document(
                id=str(uuid.uuid4()),
                content=doc.content,
                meta={
                    **doc.model_dump(exclude={"content", "external_id"}),
                    "file_id": file_id,
                    "collection_name": collection_name,
                },
            )
            for doc in doc_list
        ]
        await doc_write_pipeline.run(documents)

    async def _get_file_chunks(self, collection_name: str, file_id: int) -> List:
        chunks, _ = await self.client.scroll(
            collection_name=collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="meta.file_id",
                        match=MatchValue(value=file_id),
                    )
                ]
            ),
            limit=10000,
            with_payload=False,
        )
        return chunks

    async def preview_chunks(
        self,
        file: UploadFile,
        max_chars: int = 600,
        overlap: int = 100,
    ) -> tuple[str, List[DocumentData]]:
        """预览分块，不入库，返回 preview_id 用于后续上传复用"""
        if not file or not file.filename:
            raise ValueError("文件名为空")

        content = await file.read()
        temp_path = self._save_file(content, file.filename, "temp_preview")
        try:
            file_type = get_file_type(file.filename)
            doc_list = await self._parse_file(temp_path, file_type, max_chars, overlap)
            preview_id = await preview_cache.set(content, max_chars, overlap, doc_list)
            return preview_id, doc_list
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


file_service = FileService()
