"""
数据迁移脚本：将现有知识点迁移到文件管理体系

使用方法:
    python -m chat2rag.tools.migrate_to_file_system
"""

import asyncio
import os
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from qdrant_client.models import FieldCondition, Filter, MatchValue

from chat2rag.core.enums import FileStatus, FileType
from chat2rag.core.logger import get_logger
from chat2rag.models import File, FileVersion
from chat2rag.utils.qdrant_store import get_client

logger = get_logger(__name__)


def get_file_type_from_path(file_path: str) -> FileType:
    ext = os.path.splitext(file_path)[1].lower()
    type_map = {
        ".pdf": FileType.PDF,
        ".docx": FileType.DOCX,
        ".doc": FileType.DOCX,
        ".xlsx": FileType.XLSX,
        ".xls": FileType.XLS,
        ".csv": FileType.CSV,
        ".tsv": FileType.TSV,
        ".json": FileType.JSON,
    }
    return type_map.get(ext, FileType.UNKNOWN)


def get_filename_from_path(file_path: str) -> str:
    return os.path.basename(file_path)


async def get_all_collections():
    client = get_client()
    result = await client.get_collections()
    collections = [
        c.name for c in result.collections if c.name not in ["Document", "questions"]
    ]
    return collections


async def get_all_documents(collection_name: str):
    client = get_client()
    points, _ = await client.scroll(
        collection_name=collection_name,
        limit=100000,
        with_payload=True,
        with_vectors=False,
    )
    return points


async def update_document_file_id(collection_name: str, doc_id: str, file_id: int):
    client = get_client()
    await client.set_payload(
        collection_name=collection_name,
        payload={"meta": {"file_id": file_id}},
        points=[doc_id],
    )


async def migrate_collection(collection_name: str):
    logger.info(f"开始迁移知识库: {collection_name}")

    documents = await get_all_documents(collection_name)
    if not documents:
        logger.info(f"知识库 {collection_name} 为空，跳过")
        return

    file_path_groups = defaultdict(list)
    no_file_path_docs = []

    for doc in documents:
        payload = doc.payload or {}
        meta = payload.get("meta", {})
        source = meta.get("source", {})
        file_path = source.get("file_path") if source else None

        if file_path and file_path not in ["json", "uploads/documents", ""]:
            file_path_groups[file_path].append(doc)
        else:
            no_file_path_docs.append(doc)

    created_files = []

    for file_path, docs in file_path_groups.items():
        filename = get_filename_from_path(file_path)
        file_type = get_file_type_from_path(file_path)

        file_size = 0
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)

        existing_file = await File.get_or_none(
            collection_name=collection_name,
            filename=filename,
        )

        if existing_file:
            file_record = existing_file
            logger.info(f"文件已存在: {filename}, ID: {file_record.id}")
        else:
            file_record = await File.create(
                collection_name=collection_name,
                filename=filename,
                file_type=file_type,
                file_size=file_size,
                file_path=file_path if os.path.exists(file_path) else None,
                status=FileStatus.PARSED,
                version=1,
                chunk_count=len(docs),
                parse_config={"maxChars": 600, "overlap": 100},
            )

            await FileVersion.create(
                file_id=file_record.id,
                version=1,
                file_path=file_path if os.path.exists(file_path) else None,
                file_size=file_size,
                change_note="历史数据迁移",
                chunk_count=len(docs),
                parse_config={"maxChars": 600, "overlap": 100},
            )

            logger.info(
                f"创建文件记录: {filename}, ID: {file_record.id}, 分块数: {len(docs)}"
            )

        created_files.append(file_record)

        for doc in docs:
            await update_document_file_id(collection_name, str(doc.id), file_record.id)

    if no_file_path_docs:
        logger.info(
            f"为 {len(no_file_path_docs)} 个无文件路径的知识点创建'历史导入'文件"
        )

        history_file = await File.get_or_none(
            collection_name=collection_name,
            filename="历史导入",
        )

        if not history_file:
            history_file = await File.create(
                collection_name=collection_name,
                filename="历史导入",
                file_type=FileType.UNKNOWN,
                file_size=0,
                file_path=None,
                status=FileStatus.PARSED,
                version=1,
                chunk_count=len(no_file_path_docs),
                description="历史数据迁移时自动创建",
            )

            await FileVersion.create(
                file_id=history_file.id,
                version=1,
                file_path=None,
                file_size=0,
                change_note="历史数据迁移",
                chunk_count=len(no_file_path_docs),
            )
        else:
            history_file.chunk_count += len(no_file_path_docs)
            await history_file.save()

        for doc in no_file_path_docs:
            await update_document_file_id(collection_name, str(doc.id), history_file.id)

        created_files.append(history_file)

    logger.info(
        f"知识库 {collection_name} 迁移完成，创建 {len(created_files)} 个文件记录"
    )
    return created_files


async def run_migration():
    from tortoise import Tortoise
    from chat2rag.config.database import TORTOISE_ORM

    await Tortoise.init(config=TORTOISE_ORM)

    await Tortoise.generate_schemas()

    logger.info("开始数据迁移...")

    collections = await get_all_collections()
    logger.info(f"发现 {len(collections)} 个知识库")

    total_files = 0
    for collection_name in collections:
        files = await migrate_collection(collection_name)
        if files:
            total_files += len(files)

    logger.info(f"数据迁移完成！共创建 {total_files} 个文件记录")

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(run_migration())
