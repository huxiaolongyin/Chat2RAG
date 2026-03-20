import warnings
from math import ceil
from typing import List

from fastapi import APIRouter, Body, File, Query, UploadFile

from chat2rag.core.enums import (
    CollectionSortField,
    DocumentSortField,
    DocumentType,
    FileStatus,
    SortOrder,
)
from chat2rag.core.exceptions import ValueNoExist
from chat2rag.core.logger import get_logger
from chat2rag.dataclass.document import QADocument
from chat2rag.schemas.base import BaseResponse
from chat2rag.schemas.common import Current, Size
from chat2rag.schemas.document import (
    ChunkData,
    CollectionPaginatedData,
    FileData,
    FileVersionData,
    ReindexResult,
)
from chat2rag.services.collection_service import collection_service, document_service
from chat2rag.services.file_service import file_service
from chat2rag.utils.monitoring import async_performance_logger

logger = get_logger(__name__)
router = APIRouter()


@async_performance_logger
@router.get(
    "/collection",
    response_model=BaseResponse[CollectionPaginatedData],
    summary="获取知识库列表",
)
async def get_collections(
    current: Current = 1,
    size: Size = 10,
    collection_name: str | None = Query(None, description="知识库名称", alias="collectionName"),
    sort_by: CollectionSortField = Query(CollectionSortField.COLLECTION_NAME, description="排序字段", alias="sortBy"),
    sort_order: SortOrder = Query(SortOrder.DESC, description="排序方向", alias="sortOrder"),
):
    total, paginated_collections = await collection_service.get_list(
        current, size, sort_by, sort_order, collection_name
    )

    logger.info(f"Fetched knowledge collections: collection={collection_name}, total={total}")
    data = CollectionPaginatedData.create(items=paginated_collections, current=current, total=total, size=size)

    return BaseResponse.success(data=data)


@async_performance_logger
@router.post("/collection", response_model=BaseResponse, summary="创建新的知识库")
async def create_collection(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
):
    await collection_service.create(collection_name)
    return BaseResponse.success(msg="知识库创建成功")


@router.delete("/collection", response_model=BaseResponse, summary="删除知识库")
async def delete_collection(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
):
    await collection_service.remove(collection_name)
    return BaseResponse.success(msg="知识库删除成功")


@async_performance_logger
@router.post(
    "/collection/reindex",
    response_model=BaseResponse[ReindexResult],
    summary="重新索引知识库",
)
async def reindex_collection(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    backup: bool = Query(True, description="是否备份数据"),
    sync_files: bool = Query(True, description="是否同步文件信息到数据库", alias="syncFiles"),
):
    result = await collection_service.reindex(collection_name, backup=backup, sync_files=sync_files)
    return BaseResponse.success(msg="重新索引成功", data=result)


@async_performance_logger
@router.get("/collection/file", response_model=BaseResponse, summary="获取文件列表")
async def get_files(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    current: int = Query(1, ge=1, description="当前页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    filename: str | None = Query(None, description="文件名搜索"),
    status: FileStatus | None = Query(None, description="状态筛选"),
):
    total, files = await file_service.get_list(
        collection_name=collection_name,
        current=current,
        size=size,
        filename=filename,
        status=status,
    )

    file_list: List[FileData] = [
        FileData(
            id=f.id,
            collection_name=f.collection_name,
            filename=f.filename,
            file_type=f.file_type,
            file_size=f.file_size,
            file_path=f.file_path,
            status=f.status,
            version=f.version,
            chunk_count=f.chunk_count,
            parse_config=f.parse_config,
            error_message=f.error_message,
            create_time=f.create_time,
            update_time=f.update_time,
        )
        for f in files
    ]

    return BaseResponse.success(
        data={
            "fileList": [f.model_dump(by_alias=True) for f in file_list],
            "total": total,
            "current": current,
            "size": size,
            "pages": ceil(total / size) if total > 0 else 0,
        }
    )


@async_performance_logger
@router.post("/collection/file/preview", response_model=BaseResponse, summary="预览分块")
async def preview_file_chunks(
    file: UploadFile = File(..., description="上传文件"),
    max_chars: int = Query(600, description="分块最大字符数", alias="maxChars"),
    overlap: int = Query(100, description="分块重叠字符数"),
):
    """预览文件分块结果，不保存到数据库。返回 previewId 可在上传时复用，避免重复调用大模型。"""
    preview_id, doc_list = await file_service.preview_chunks(file, max_chars, overlap)
    chunks = [{"content": doc.content, "chunkIndex": doc.chunk_index} for doc in doc_list]
    return BaseResponse.success(
        data={
            "filename": file.filename,
            "chunks": chunks,
            "chunkCount": len(chunks),
            "previewId": preview_id,
        }
    )


@async_performance_logger
@router.get("/collection/file/{file_id}", response_model=BaseResponse, summary="获取文件详情")
async def get_file_detail(
    file_id: int,
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    current: int = Query(1, ge=1, description="当前页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    print(file_id, type(file_id))
    if file_id == -1:
        from chat2rag.core.enums import FileType

        chunk_total, chunks = await file_service.get_chunks(
            collection_name=collection_name,
            file_id=file_id,
            current=current,
            size=size,
        )
        file_data = FileData(
            id=-1,
            collection_name=collection_name,
            filename="JSON导入",
            file_type=FileType.JSON,
            file_size=0,
            status=FileStatus.PARSED,
            version=1,
            chunk_count=chunk_total,
        )
    else:
        db_file = await file_service.get_by_id(file_id)
        if not db_file:
            raise ValueNoExist(f"文件不存在: {file_id}")

        chunk_total, chunks = await file_service.get_chunks(
            collection_name=collection_name,
            file_id=file_id,
            current=current,
            size=size,
        )

        file_data = FileData(
            id=db_file.id,
            collection_name=db_file.collection_name,
            filename=db_file.filename,
            file_type=db_file.file_type,
            file_size=db_file.file_size,
            status=db_file.status,
            version=db_file.version,
            chunk_count=db_file.chunk_count,
            parse_config=db_file.parse_config,
            error_message=db_file.error_message,
            create_time=db_file.create_time,
            update_time=db_file.update_time,
        )

    chunk_list = [ChunkData(id=c["id"], content=c["content"], chunk_index=c.get("chunkIndex")) for c in chunks]

    return BaseResponse.success(
        data={
            "file": file_data.model_dump(by_alias=True),
            "chunks": [c.model_dump() for c in chunk_list],
            "chunkTotal": chunk_total,
            "current": current,
            "size": size,
        }
    )


@async_performance_logger
@router.post("/collection/file", response_model=BaseResponse, summary="上传文件")
async def upload_file(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    file: UploadFile | None = File(None, description="上传文件"),
    max_chars: int = Query(600, description="分块最大字符数", alias="maxChars"),
    overlap: int = Query(100, description="分块重叠字符数"),
    preview_id: str | None = Query(None, description="预览ID，用于复用预览时的分块结果", alias="previewId"),
):
    if not await collection_service.client.collection_exists(collection_name):
        raise ValueNoExist(f"知识库<{collection_name}>不存在")

    if not file:
        return BaseResponse.error(msg="请上传文件")

    db_file, _ = await file_service.create(
        collection_name=collection_name,
        file=file,
        max_chars=max_chars,
        overlap=overlap,
        preview_id=preview_id,
    )

    return BaseResponse.success(
        msg="文件上传成功",
        data={
            "fileId": db_file.id,
            "chunkCount": db_file.chunk_count,
            "status": db_file.status.value,
        },
    )


@async_performance_logger
@router.delete("/collection/file/{file_id}", response_model=BaseResponse, summary="删除文件")
async def delete_file(
    file_id: int,
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
):
    await file_service.delete(file_id)
    return BaseResponse.success(msg="文件删除成功")


@async_performance_logger
@router.post(
    "/collection/file/{file_id}/version",
    response_model=BaseResponse,
    summary="上传新版本",
)
async def create_file_version(
    file_id: int,
    file: UploadFile = File(..., description="新版本文件"),
    change_note: str | None = Query(None, description="变更说明", alias="changeNote"),
    max_chars: int = Query(600, description="分块最大字符数", alias="maxChars"),
    overlap: int = Query(100, description="分块重叠字符数"),
):
    db_file = await file_service.create_version(
        file_id=file_id,
        file=file,
        change_note=change_note,
        max_chars=max_chars,
        overlap=overlap,
    )
    return BaseResponse.success(
        msg="版本上传成功",
        data={
            "fileId": db_file.id,
            "version": db_file.version,
            "chunkCount": db_file.chunk_count,
        },
    )


@async_performance_logger
@router.get(
    "/collection/file/{file_id}/versions",
    response_model=BaseResponse,
    summary="获取版本历史",
)
async def get_file_versions(file_id: int):
    versions = await file_service.get_versions(file_id)

    version_list = [
        FileVersionData(
            id=v.id,
            version=v.version,
            file_size=v.file_size,
            file_path=v.file_path,
            change_note=v.change_note,
            chunk_count=v.chunk_count,
            parse_config=v.parse_config,
            create_time=v.create_time,
        )
        for v in versions
    ]

    return BaseResponse.success(data={"versions": [v.model_dump(by_alias=True) for v in version_list]})


@async_performance_logger
@router.post(
    "/collection/file/{file_id}/rollback/{version}",
    response_model=BaseResponse,
    summary="回滚到指定版本",
)
async def rollback_file_version(
    file_id: int,
    version: int,
):
    db_file = await file_service.rollback(file_id=file_id, version=version)
    return BaseResponse.success(
        msg=f"已回滚到版本 {version}",
        data={
            "fileId": db_file.id,
            "version": db_file.version,
            "chunkCount": db_file.chunk_count,
        },
    )


@async_performance_logger
@router.post(
    "/collection/file/{file_id}/reparse",
    response_model=BaseResponse,
    summary="重新解析文件",
)
async def reparse_file(
    file_id: int,
    max_chars: int = Query(600, description="分块最大字符数", alias="maxChars"),
    overlap: int = Query(100, description="分块重叠字符数"),
):
    db_file = await file_service.reparse(file_id=file_id, max_chars=max_chars, overlap=overlap)
    return BaseResponse.success(
        msg="重新解析成功",
        data={
            "fileId": db_file.id,
            "version": db_file.version,
            "chunkCount": db_file.chunk_count,
        },
    )


@async_performance_logger
@router.get("/collection/document", response_model=BaseResponse, summary="获取知识库所有文档")
async def get_documents(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    current: int = Query(1, ge=1, description="当前页码，默认1"),
    size: int = Query(10, ge=1, le=10000, description="每页数量(1-10000)，默认10"),
    document_content: str | None = Query(None, description="文档内容", alias="documentContent"),
    file_id: int | None = Query(None, description="文件ID过滤", alias="fileId"),
    file_path: str | None = Query(None, description="文件路径过滤(兼容旧版)", alias="filePath"),
    sort_by: DocumentSortField = Query(DocumentSortField.DOCUMENT_CONTENT, description="排序字段", alias="sortBy"),
    sort_order: str = Query("desc", description="排序方向(asc, desc)，默认 desc", alias="sortOrder"),
):
    from chat2rag.core.enums import SortOrder

    sort_order_enum = SortOrder.DESC if sort_order.lower() == "desc" else SortOrder.ASC

    total, paginated_docs = await document_service.get_list(
        collection_name=collection_name,
        current=current,
        size=size,
        sort_by=sort_by,
        sort_order=sort_order_enum,
        document_content=document_content,
        file_id=file_id,
        file_path=file_path,
    )
    logger.info(f"Fetched documents: collection='{collection_name}', total={total}")

    return BaseResponse.success(
        data={
            "docList": paginated_docs,
            "current": current,
            "size": size,
            "total": total,
            "pages": ceil(total / size),
        },
    )


@async_performance_logger
@router.post("/collection/document", response_model=BaseResponse, summary="从JSON内容创建知识")
async def create_documents_by_json(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    doc_list: List[QADocument] = Body(description="知识内容", alias="docList"),
):
    if not await collection_service.client.collection_exists(collection_name):
        raise ValueNoExist(f"知识库<{collection_name}>不存在")

    await document_service.create_by_json(collection_name, doc_list)

    return BaseResponse.success(msg="知识内容创建成功", data={"collectionName": collection_name})


@async_performance_logger
@router.post(
    "/collection/document/file",
    response_model=BaseResponse,
    summary="[已废弃] 从文件创建知识",
    deprecated=True,
)
async def create_documents_by_file(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    file: UploadFile | None = File(None, description="上传知识文件 (CSV/XLSX/PDF/DOCX/TSV)"),
    max_chars: int = Query(600, description="分块最大字符数(DOCX/PDF)", alias="maxChars"),
    overlap: int = Query(100, description="分块重叠字符数(DOCX/PDF)"),
):
    warnings.warn(
        "POST /collection/document/file 接口已废弃，请使用 POST /collection/file",
        DeprecationWarning,
        stacklevel=2,
    )

    if not await collection_service.client.collection_exists(collection_name):
        raise ValueNoExist(f"知识库<{collection_name}>不存在")

    if not file:
        return BaseResponse.error(msg="请上传文件")

    db_file, _ = await file_service.create(
        collection_name=collection_name,
        file=file,
        max_chars=max_chars,
        overlap=overlap,
    )

    return BaseResponse.success(
        msg="[已废弃] 建议使用 POST /collection/file 接口",
        data={
            "fileId": db_file.id,
            "chunkCount": db_file.chunk_count,
            "deprecationWarning": "此接口已废弃，请使用 POST /collection/file",
        },
    )


@async_performance_logger
@router.delete("/collection/document", response_model=BaseResponse, summary="删除知识")
async def delete_documents(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    doc_id_list: List[str] = Body(description="知识的id", alias="docIdList"),
):
    data = await document_service.remove(collection_name=collection_name, doc_id_list=doc_id_list)
    return BaseResponse.success(msg="删除知识成功", data=data)


@async_performance_logger
@router.get("/query", response_model=BaseResponse, summary="知识内容查询")
async def query_documents(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    query: str = Query(description="查询内容"),
    top_k: int = Query(default=5, ge=1, le=30, description="返回数量(1-30), 默认5", alias="topK"),
    score_threshold: float | None = Query(
        default=None,
        description="分数阈值(0-1.00)，question默认0.65，qa_pair默认0.88",
        alias="scoreThreshold",
    ),
    doc_type: DocumentType = Query(
        default=DocumentType.QA_PAIR,
        description="查询类型(question, qa_pair)",
        alias="type",
    ),
):
    doc_list = await document_service.query(
        collection_name,
        query,
        top_k=top_k,
        score_threshold=score_threshold,
        doc_type=doc_type,
    )

    data = {
        "collectionName": collection_name,
        "docList": [{"id": doc.id, "content": doc.content, "score": doc.score} for doc in doc_list],
        "topK": top_k,
        "scoreThreshold": score_threshold,
    }
    logger.info(f"Query knowledge completed: collection='{collection_name}', results={len(doc_list)}")

    return BaseResponse.success(data=data)


@async_performance_logger
@router.get("/exact-query", response_model=BaseResponse, summary="精确知识查询")
async def exact_query(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    query: str = Query(description="查询内容"),
):
    answer_document = await document_service.query_exact(collection_name, query)
    if answer_document:
        return BaseResponse.success(
            data={
                "collectionName": collection_name,
                "query": query,
                "answer": answer_document.meta["answer"],
            }
        )
    else:
        logger.info(f"Exact match returned no results: collection='{collection_name}', query='{query}'")
        return BaseResponse.success(data={"collectionName": collection_name, "query": query, "answer": None})
