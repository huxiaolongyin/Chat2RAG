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
    collection_name: str | None = Query(
        None, description="知识库名称", alias="collectionName"
    ),
    sort_by: CollectionSortField = Query(
        CollectionSortField.COLLECTION_NAME, description="排序字段", alias="sortBy"
    ),
    sort_order: SortOrder = Query(
        SortOrder.DESC, description="排序方向", alias="sortOrder"
    ),
):
    total, paginated_collections = await collection_service.get_list(
        current, size, sort_by, sort_order, collection_name
    )

    logger.info(
        f"Fetched knowledge collections: collection={collection_name}, total={total}"
    )
    data = CollectionPaginatedData.create(
        items=paginated_collections, current=current, total=total, size=size
    )

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
):
    result = await collection_service.reindex(collection_name, backup=backup)
    return BaseResponse.success(msg="重新索引成功", data=result)


# ==================== 文件管理 API ====================


@async_performance_logger
@router.get(
    "/collection/file",
    response_model=BaseResponse,
    summary="获取文件列表",
)
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

    file_list = []
    for f in files:
        file_list.append(
            FileData(
                id=f.id,
                collection_name=f.collection_name,
                filename=f.filename,
                file_type=f.file_type,
                file_size=f.file_size,
                status=f.status,
                version=f.version,
                chunk_count=f.chunk_count,
                parse_config=f.parse_config,
                error_message=f.error_message,
                create_time=f.create_time,
                update_time=f.update_time,
            )
        )

    return BaseResponse.success(
        data={
            "fileList": [f.model_dump() for f in file_list],
            "total": total,
            "current": current,
            "size": size,
            "pages": ceil(total / size) if total > 0 else 0,
        }
    )


@async_performance_logger
@router.get(
    "/collection/file/{file_id}",
    response_model=BaseResponse,
    summary="获取文件详情",
)
async def get_file_detail(
    file_id: int,
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    current: int = Query(1, ge=1, description="当前页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
):
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

    chunk_list = [
        ChunkData(id=c["id"], content=c["content"], chunk_index=c.get("chunkIndex"))
        for c in chunks
    ]

    return BaseResponse.success(
        data={
            "file": file_data.model_dump(),
            "chunks": [c.model_dump() for c in chunk_list],
            "chunkTotal": chunk_total,
            "current": current,
            "size": size,
        }
    )


@async_performance_logger
@router.post(
    "/collection/file",
    response_model=BaseResponse,
    summary="上传文件",
)
async def upload_file(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    file: UploadFile | None = File(None, description="上传文件"),
    preview: bool = Query(False, description="是否仅预览"),
    max_chars: int = Query(600, description="分块最大字符数", alias="maxChars"),
    overlap: int = Query(100, description="分块重叠字符数"),
):
    if not await collection_service.client.collection_exists(collection_name):
        raise ValueNoExist(f"知识库<{collection_name}>不存在")

    if not file:
        return BaseResponse.error(msg="请上传文件")

    db_file, doc_list = await file_service.create(
        collection_name=collection_name,
        file=file,
        max_chars=max_chars,
        overlap=overlap,
        preview=preview,
    )

    if preview and doc_list:
        preview_data = [
            {
                "docType": doc.doc_type,
                "content": doc.content,
                "answer": doc.answer,
            }
            for doc in doc_list
        ]
        return BaseResponse.success(
            msg="预览成功",
            data={
                "fileId": db_file.id,
                "previewList": preview_data,
            },
        )

    return BaseResponse.success(
        msg="文件上传成功",
        data={"fileId": db_file.id, "chunkCount": db_file.chunk_count},
    )


@async_performance_logger
@router.post(
    "/collection/file/{file_id}/confirm",
    response_model=BaseResponse,
    summary="确认上传预览文件",
)
async def confirm_file_upload(
    file_id: int,
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
):
    return BaseResponse.success(msg="请使用 /collection/file 接口的 preview=false 参数")


@async_performance_logger
@router.delete(
    "/collection/file/{file_id}",
    response_model=BaseResponse,
    summary="删除文件",
)
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
            change_note=v.change_note,
            chunk_count=v.chunk_count,
            parse_config=v.parse_config,
            create_time=v.create_time,
        )
        for v in versions
    ]

    return BaseResponse.success(
        data={"versions": [v.model_dump() for v in version_list]}
    )


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
    db_file = await file_service.reparse(
        file_id=file_id, max_chars=max_chars, overlap=overlap
    )
    return BaseResponse.success(
        msg="重新解析成功",
        data={
            "fileId": db_file.id,
            "version": db_file.version,
            "chunkCount": db_file.chunk_count,
        },
    )


# ==================== 知识点管理 API (保留兼容) ====================


@async_performance_logger
@router.get(
    "/collection/document", response_model=BaseResponse, summary="获取知识库所有文档"
)
async def get_documents(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    current: int = Query(1, ge=1, description="当前页码，默认1"),
    size: int = Query(10, ge=1, le=10000, description="每页数量(1-10000)，默认10"),
    document_content: str | None = Query(
        None, description="文档内容", alias="documentContent"
    ),
    sort_by: DocumentSortField = Query(
        DocumentSortField.DOCUMENT_CONTENT, description="排序字段", alias="sortBy"
    ),
    sort_order: SortOrder = Query(
        SortOrder.DESC, description="排序方向(asc, desc)，默认 desc", alias="sortOrder"
    ),
):
    total, paginated_docs = await document_service.get_list(
        collection_name=collection_name,
        current=current,
        size=size,
        sort_by=sort_by,
        sort_order=sort_order,
        document_content=document_content,
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
@router.post(
    "/collection/document", response_model=BaseResponse, summary="从json内容创建知识"
)
async def create_documents_by_json(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    doc_list: List[QADocument] = Body(description="知识内容", alias="docList"),
):
    if not await collection_service.client.collection_exists(collection_name):
        raise ValueNoExist(f"知识库<{collection_name}>不存在")

    await document_service.create_by_json(collection_name, doc_list)

    return BaseResponse.success(
        msg="知识内容创建成功", data={"collectionName": collection_name}
    )


@async_performance_logger
@router.post(
    "/collection/document/file",
    response_model=BaseResponse,
    summary="从文件进行创建知识",
)
async def create_documents_by_file(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    file: UploadFile | None = File(
        None, description="上传知识文件 (CSV/XLSX/PDF/DOCX/TSV)"
    ),
    preview: bool = Query(False, description="是否仅预览，不实际导入"),
    max_chars: int = Query(
        600, description="分块最大字符数(DOCX/PDF)", alias="maxChars"
    ),
    overlap: int = Query(100, description="分块重叠字符数(DOCX/PDF)"),
    cache_id: str | None = Query(
        None, description="缓存ID，从缓存导入时使用", alias="cacheId"
    ),
):
    if not await collection_service.client.collection_exists(collection_name):
        raise ValueNoExist(f"知识库<{collection_name}>不存在")

    if cache_id and not preview:
        await document_service.create_from_cache(cache_id, collection_name)
        return BaseResponse.success(
            msg="知识内容创建成功", data={"collectionName": collection_name}
        )

    if not file:
        return BaseResponse.error(msg="请上传文件")

    cache_id_result, doc_list = await document_service.create(
        collection_name, file, preview=preview, max_chars=max_chars, overlap=overlap
    )

    if preview and doc_list:
        preview_data = [
            {
                "docType": doc.doc_type,
                "content": doc.content,
                "answer": doc.answer,
                "source": doc.source.model_dump() if doc.source else None,
            }
            for doc in doc_list
        ]
        return BaseResponse.success(
            msg="预览成功",
            data={
                "collectionName": collection_name,
                "previewList": preview_data,
                "cacheId": cache_id_result,
            },
        )

    return BaseResponse.success(
        msg="知识内容创建中", data={"collectionName": collection_name}
    )


@async_performance_logger
@router.delete("/collection/document", response_model=BaseResponse, summary="删除知识")
async def delete_documents(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    doc_id_list: List[str] = Body(description="知识的id", alias="docIdList"),
):
    data = await document_service.remove(
        collection_name=collection_name, doc_id_list=doc_id_list
    )
    return BaseResponse.success(msg="删除知识成功", data=data)


@async_performance_logger
@router.get("/query", response_model=BaseResponse, summary="知识内容查询")
async def query_documents(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    query: str = Query(description="查询内容"),
    top_k: int = Query(
        default=5, ge=1, le=30, description="返回数量(1-30), 默认5", alias="topK"
    ),
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
        "docList": [
            {"id": doc.id, "content": doc.content, "score": doc.score}
            for doc in doc_list
        ],
        "topK": top_k,
        "scoreThreshold": score_threshold,
    }
    logger.info(
        f"Query knowledge completed: collection='{collection_name}', results={len(doc_list)}"
    )

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
        logger.info(
            f"Exact match returned no results: collection='{collection_name}', query='{query}'"
        )
        return BaseResponse.success(
            data={"collectionName": collection_name, "query": query, "answer": None}
        )
