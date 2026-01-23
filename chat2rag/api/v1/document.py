from math import ceil
from typing import List

from fastapi import APIRouter, BackgroundTasks, Body, File, Query, UploadFile

from chat2rag.core.enums import (
    CollectionSortField,
    DocumentSortField,
    DocumentType,
    SortOrder,
)
from chat2rag.core.exceptions import ValueNoExist
from chat2rag.core.logger import get_logger
from chat2rag.schemas.base import BaseResponse
from chat2rag.schemas.common import Current, Size
from chat2rag.schemas.document import CollectionPaginatedData
from chat2rag.services.collection_service import collection_service, document_service
from chat2rag.utils.monitoring import async_performance_logger

logger = get_logger(__name__)
router = APIRouter()


@async_performance_logger
@router.get("/collection", response_model=BaseResponse[CollectionPaginatedData], summary="获取知识库列表")
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

    logger.info(
        f"The list of knowledge collections is successfully obtained. Collection name: <{collection_name}>; Total: <{total}>;"
    )
    data = CollectionPaginatedData.create(items=paginated_collections, current=current, total=total, size=size)

    # 返回分页数据
    return BaseResponse.success(data=data)


@async_performance_logger
@router.post("/collection", response_model=BaseResponse, summary="创建新的知识库")
async def create_collection(collection_name: str = Query(description="知识库名称", alias="collectionName")):
    await collection_service.create(collection_name)
    return BaseResponse.success(msg="知识库创建成功")


@router.delete("/collection", response_model=BaseResponse, summary="删除知识库")
async def delete_collection(collection_name: str = Query(description="知识库名称", alias="collectionName")):
    await collection_service.remove(collection_name)
    return BaseResponse.success(msg="知识库删除成功")


@async_performance_logger
@router.get("/collection/document", response_model=BaseResponse, summary="获取知识库所有文档")
async def get_documents(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    current: int = Query(1, ge=1, description="当前页码，默认1"),
    size: int = Query(10, ge=1, le=10000, description="每页数量(1-10000)，默认10"),
    document_content: str | None = Query(None, description="文档内容", alias="documentContent"),
    sort_by: DocumentSortField = Query(DocumentSortField.DOCUMENT_CONTENT, description="排序字段", alias="sortBy"),
    sort_order: SortOrder = Query(SortOrder.DESC, description="排序方向(asc, desc)，默认 desc", alias="sortOrder"),
):
    total, paginated_docs = await document_service.get_list(
        collection_name=collection_name,
        current=current,
        size=size,
        sort_by=sort_by,
        sort_order=sort_order,
        document_content=document_content,
    )
    logger.info(
        f"The documents of collection is successfully obtained. Collection name: <{collection_name}>; Total: <{total}>;"
    )

    # 返回分页数据
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
@router.post("/collection/document", response_model=BaseResponse, summary="创建知识")
async def create_documents(
    background_tasks: BackgroundTasks,
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    file: UploadFile = File(description="上传知识文件 (CSV/XLSX/PDF)"),
):
    if not await collection_service.client.collection_exists(collection_name):
        raise ValueNoExist(f"知识库<{collection_name}>不存在")

    # 后台执行内容创建
    background_tasks.add_task(document_service.create, collection_name, file)

    return BaseResponse.success(
        msg="知识内容创建中",
        data={"collectionName": collection_name},
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
        default=None, description="分数阈值(0-1.00)，question默认0.65，qa_pair默认0.88", alias="scoreThreshold"
    ),
    doc_type: DocumentType = Query(
        default=DocumentType.QA_PAIR, description="查询类型(question, qa_pair)", alias="type"
    ),
):
    """
    在知识库中查询文档
    - query: 查询文本
    - type: 查询类型，question或qa_pair
    - top_k: 返回的最大结果数
    - score_threshold: 相似度分数阈值
    """

    doc_list = await document_service.query(
        collection_name, query, top_k=top_k, score_threshold=score_threshold, doc_type=doc_type
    )

    data = {
        "collectionName": collection_name,
        "docList": [{"id": doc.id, "content": doc.content, "score": doc.score} for doc in doc_list],
        "topK": top_k,
        "scoreThreshold": score_threshold,
    }
    logger.info(f"Knowledge query success. Collection name: <{collection_name}>; Number of results: <{len(doc_list)}>")

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
        logger.info(f"Exact query found no results. Collection name: <{collection_name}>; Query: <{query}>")
        return BaseResponse.success(
            data={
                "collectionName": collection_name,
                "query": query,
                "answer": None,
            }
        )
