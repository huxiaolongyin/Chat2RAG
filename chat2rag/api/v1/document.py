from math import ceil
from typing import Any, Dict, List

from fastapi import APIRouter, Body, Query

from chat2rag.config import CONFIG
from chat2rag.core.enums import (
    CollectionSortField,
    DocumentSortField,
    DocumentType,
    SortOrder,
)
from chat2rag.core.exceptions import ValueNoExist
from chat2rag.core.logger import get_logger
from chat2rag.dataclass.document import QADocument
from chat2rag.schemas.base import BaseResponse
from chat2rag.schemas.common import Current, Size
from chat2rag.schemas.document import collectionPaginatedData
from chat2rag.services.collection_service import collection_service, document_service
from chat2rag.stores.qdrant import QAQdrantDocumentStore
from chat2rag.utils.monitoring import async_performance_logger

logger = get_logger(__name__)
router = APIRouter()


@async_performance_logger
@router.get("/collection", response_model=BaseResponse[collectionPaginatedData], summary="获取知识库列表")
async def get_collections(
    current: Current = 1,
    size: Size = 10,
    collection_name: str | None = Query(None, description="知识库名称", alias="collectionName"),
    sort_by: CollectionSortField = Query(CollectionSortField.COLLECTION_NAME, description="排序字段", alias="sortBy"),
    sort_order: SortOrder = Query(SortOrder.DESC, description="排序方向", alias="sortOrder"),
):
    total, paginated_collections = collection_service.get_list(current, size, sort_by, sort_order, collection_name)

    logger.info(
        f"The list of knowledge collections is successfully obtained. Collection name: <{collection_name}>; Total: <{total}>;"
    )
    data = collectionPaginatedData.create(items=paginated_collections, current=current, total=total, size=size)

    # 返回分页数据
    return BaseResponse.success(data=data)


@async_performance_logger
@router.post("/collection", response_model=BaseResponse, summary="创建新的知识库")
async def create_collection(collection_name: str = Query(description="知识库名称", alias="collectionName")):
    collection_service.create(collection_name)
    return BaseResponse.success(msg="知识库创建成功")


@router.delete("/collection", response_model=BaseResponse, summary="删除知识库")
async def delete_collection(collection_name: str):
    collection_service.remove(collection_name)
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
    total, paginated_docs = document_service.get_list(
        collection_name, current, size, sort_by, sort_order, document_content
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
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    doc_list: List[QADocument] = Body(description="知识内容", alias="docList"),
):
    write_docs_count = document_service.create(collection_name, doc_list)

    return BaseResponse.success(
        msg="知识创建成功",
        data={"collection_name": collection_name, "write_docs_count": write_docs_count},
    )


@async_performance_logger
@router.delete("/collection/document", response_model=BaseResponse, summary="删除知识")
async def delete_documents(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    doc_id_list: List[str] = Body(description="知识的id", alias="docIdList"),
):
    data = QAQdrantDocumentStore(collection_name).delete_documents(doc_id_list)

    return BaseResponse.success(msg="删除知识成功", data=data)


@async_performance_logger
@router.get("/query", response_model=BaseResponse, summary="知识内容查询")
async def query_documents(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    query: str = Query(description="查询内容", alias="query"),
    top_k: int = Query(default=5, ge=1, le=30, description="返回数量(1-30), 默认5", alias="topK"),
    score_threshold: float = Query(
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

    # 设置默认检索阈值
    if not score_threshold:
        score_threshold = CONFIG.PRECISION_THRESHOLD if doc_type == "question" else CONFIG.SCORE_THRESHOLD

    # start_time = time.perf_counter()
    doc = QAQdrantDocumentStore(collection_name)
    doc_list = await doc.query(
        query=query,
        top_k=top_k,
        score_threshold=score_threshold,
        filters={"field": "meta.type", "operator": "==", "value": doc_type},
    )

    processed_docs = [{"id": doc.id, "content": doc.content, "score": doc.score} for doc in doc_list]

    data = {
        "collectionName": collection_name,
        "docList": processed_docs,
        "topK": top_k,
        "scoreThreshold": score_threshold,
    }
    logger.info(
        f"Knowledge query success. Collection name: <{collection_name}>; Number of results: <{len(processed_docs)}>"
    )

    return BaseResponse.success(data=data)


@async_performance_logger
@router.get("/exact-query", response_model=BaseResponse, summary="精确知识查询")
async def exact_query(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    query: str = Query(description="查询内容", alias="query"),
):

    doc_store = QAQdrantDocumentStore(collection_name)
    answer = await doc_store.query_exact(query=query)

    if answer:
        logger.info(f"Exact query success. Collection name: <{collection_name}>; Found answer")
        return BaseResponse.success(
            data={
                "collection_name": collection_name,
                "query": query,
                "answer": answer,
            }
        )
    else:
        logger.info(f"Exact query found no results. Collection name: <{collection_name}>; Query: <{query}>")
        return BaseResponse.success(
            data={
                "collection_name": collection_name,
                "query": query,
                "answer": None,
            }
        )


@async_performance_logger
@router.get("/collection/stats", response_model=BaseResponse, summary="获取知识库统计信息")
async def get_collection_stats(collection_name: str = Query(description="知识库名称", alias="collectionName")):

    doc_store = QAQdrantDocumentStore(collection_name)

    # 获取文档总数
    document_list = doc_store.get_document_list
    total_docs = len(document_list)

    # 计算平均文档长度
    if total_docs > 0:
        avg_length = sum(len(doc["content"]) for doc in document_list) / total_docs
    else:
        avg_length = 0

    stats = {
        "collectionName": collection_name,
        "totalDocuments": total_docs,
        "averageLength": round(avg_length, 2),
    }

    logger.info(f"Stats for collection <{collection_name}> retrieved successfully")
    return BaseResponse.success(data=stats)


@async_performance_logger
@router.put("/collection/document", response_model=BaseResponse, summary="更新知识")
async def update_document(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    doc_id: str = Query(description="知识ID", alias="docId"),
    updated_content: Dict[str, Any] = Body(description="更新的内容", alias="updatedContent"),
):
    """
    更新文档内容
    注意：这需要在QAQdrantDocumentStore中实现update_document方法
    """

    # 这里假设QAQdrantDocumentStore有一个update_document方法
    # 如果没有，需要先在qdrant.py中实现该方法

    # 实际实现可能需要根据QAQdrantDocumentStore的实际功能调整
    # 这里只是提供一个接口示例
    doc_store = QAQdrantDocumentStore(collection_name)

    # 先获取文档，确认存在
    docs = doc_store.filter_documents({"field": "id", "operator": "==", "value": doc_id})

    if not docs:
        logger.error(f"Document <{doc_id}> not found in collection <{collection_name}>")
        raise ValueNoExist("文档不存在")

    # 删除原文档
    doc_store.delete_documents([doc_id])

    # 创建更新后的QADocument对象
    # 注意：这里假设updated_content包含question和answer字段
    # 实际实现可能需要根据您的数据结构调整
    updated_doc = QADocument(
        question=updated_content.get("question", ""),
        answer=updated_content.get("answer", ""),
    )

    # 写入更新后的文档
    result = await doc_store.write_documents([updated_doc])

    logger.info(f"Document <{doc_id}> updated successfully in collection <{collection_name}>")
    return BaseResponse.success(msg="文档更新成功", data={"doc_id": doc_id})
