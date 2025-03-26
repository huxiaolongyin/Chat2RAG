import functools
import time
from enum import Enum
from math import ceil
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from chat2rag.api.schema import Error, Success
from chat2rag.config import CONFIG
from chat2rag.core.document.qdrant import QAQdrantDocumentStore
from chat2rag.dataclass.document import QADocument
from chat2rag.logger import logger

router = APIRouter()


# 性能监控装饰器
def timing_decorator(func: Callable):
    @functools.wraps(func)  # 保留原始函数的签名和元数据
    async def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = await func(*args, **kwargs)
        elapsed_time = time.perf_counter() - start_time
        logger.debug(
            f"API Function <{func.__name__}> took {elapsed_time:.3f} seconds to complete"
        )
        return result

    return wrapper


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class CollectionSortField(str, Enum):
    COLLECTION_NAME = "collection_name"
    DOCUMENT_COUNT = "document_count"


class DocumentSortField(str, Enum):
    DOCUMENT_CONTENT = "content"


# 依赖函数，用于检查集合是否存在
async def validate_collection(
    collection_name: str = Query(..., description="知识库名称", alias="collectionName")
):
    """验证知识库是否存在"""
    if collection_name not in QAQdrantDocumentStore().get_collection_names():
        logger.error(f"Knowledge collection <{collection_name}> does not exist.")
        raise HTTPException(status_code=404, detail="知识库不存在")
    return collection_name


@router.get("/collection", summary="获取知识库列表")
@timing_decorator
async def get_collections(
    current: int = Query(1, ge=1, description="当前页码，默认1"),
    size: int = Query(10, ge=1, le=100, description="每页数量(1-100)，默认10"),
    collection_name: Optional[str] = Query(
        None,
        description="知识库名称",
        alias="collectionName",
    ),
    sort_by: Optional[CollectionSortField] = Query(
        CollectionSortField.COLLECTION_NAME,
        description="排序字段",
        alias="sortBy",
    ),
    sort_order: Optional[SortOrder] = Query(
        SortOrder.DESC,
        description="排序方向",
        alias="sortOrder",
    ),
):
    """获取知识库列表，支持分页、搜索和排序"""
    logger.info(
        f"Getting the list of collections. Collection name: <{collection_name}>; Current: <{current}>; Page size: <{size}>"
    )

    try:
        # 获取所有数据
        collection_list = QAQdrantDocumentStore().get_collections()

        # 如果有搜索条件则过滤
        if collection_name:
            collection_list = [
                collection
                for collection in collection_list
                if collection_name.lower() in collection["collection_name"].lower()
            ]

        # 排序
        collection_list.sort(
            key=lambda x: x[sort_by], reverse=(sort_order == SortOrder.DESC)
        )

        # 计算分页
        total = len(collection_list)
        start_index = (current - 1) * size
        end_index = start_index + size
        paginated_collections = collection_list[start_index:end_index]

        logger.info(
            f"The list of knowledge collections is successfully obtained. Collection name: <{collection_name}>; Total: <{total}>;"
        )

        # 返回分页数据
        return Success(
            data={
                "collection_list": paginated_collections,
                "current": current,
                "size": size,
                "total": total,
                "pages": ceil(total / size),
            },
        )
    except Exception as e:
        logger.error(f"Failed to get collection list: {str(e)}")
        return Error(msg=f"获取知识库列表失败: {str(e)}")


@router.post("/collection", summary="创建新的知识库")
@timing_decorator
async def create_collection(
    collection_name: str = Query(
        description="知识库名称",
        alias="collectionName",
    ),
):
    """创建新的知识库"""
    logger.info(
        f"Creating a knowledge collection. Collection name: <{collection_name}>"
    )

    try:
        if collection_name in QAQdrantDocumentStore().get_collection_names():
            logger.error(
                f"The knowledge collection <{collection_name}> already exists."
            )
            return Error(msg="知识库已存在", data={"collection_name": collection_name})

        document_store = QAQdrantDocumentStore(collection_name)
        if document_store.create:
            logger.info(
                f"The knowledge collection <{collection_name}> is created successfully."
            )
            return Success(
                msg="知识库创建成功", data={"collection_name": collection_name}
            )
        else:
            logger.error(
                f"Failed to create the knowledge collection <{collection_name}>."
            )
            return Error(
                msg="知识库创建失败", data={"collection_name": collection_name}
            )
    except Exception as e:
        logger.error(f"Error creating collection {collection_name}: {str(e)}")
        return Error(
            msg=f"知识库创建失败: {str(e)}", data={"collection_name": collection_name}
        )


@router.delete("/collection", summary="删除知识库")
@timing_decorator
async def delete_collection(collection_name: str = Depends(validate_collection)):
    """删除知识库"""
    logger.info(f"Deleting knowledge collection <{collection_name}>")

    try:
        QAQdrantDocumentStore(collection_name).delete_collection
        logger.info(
            f"The knowledge collection <{collection_name}> is deleted successfully."
        )
        return Success(msg="删除知识库成功", data={"collection_name": collection_name})
    except Exception as e:
        logger.error(
            f"Failed to delete the knowledge collection <{collection_name}>. Error: {str(e)};"
        )
        return Error(msg="删除知识库失败", data=str(e))


@router.get("/collection/document", summary="获取知识库所有文档")
@timing_decorator
async def get_documents(
    collection_name: str = Depends(validate_collection),
    current: int = Query(1, ge=1, description="当前页码，默认1"),
    size: int = Query(10, ge=1, le=10000, description="每页数量(1-10000)，默认10"),
    document_content: Optional[str] = Query(
        None,
        description="文档内容",
        alias="documentContent",
    ),
    sort_by: Optional[DocumentSortField] = Query(
        DocumentSortField.DOCUMENT_CONTENT,
        description="排序字段",
        alias="sortBy",
    ),
    sort_order: Optional[SortOrder] = Query(
        SortOrder.DESC,
        description="排序方向(asc, desc)，默认 desc",
        alias="sortOrder",
    ),
):
    """获取知识库中的所有文档，支持分页、过滤和排序"""
    logger.info(
        f"Get documents of collection. Collection name: <{collection_name}>; Current: <{current}>; Page size: <{size}>"
    )

    try:
        document_list = QAQdrantDocumentStore(collection_name).get_document_list

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

        logger.info(
            f"The documents of collection is successfully obtained. Collection name: <{collection_name}>; Total: <{total}>;"
        )

        # 返回分页数据
        return Success(
            data={
                "doc_list": paginated_docs,
                "current": current,
                "size": size,
                "total": total,
                "pages": ceil(total / size),
            },
        )
    except Exception as e:
        logger.error(
            f"Error getting documents from collection {collection_name}: {str(e)}"
        )
        return Error(msg=f"获取文档失败: {str(e)}")


@router.post("/collection/document", summary="创建知识")
@timing_decorator
async def create_documents(
    collection_name: str = Depends(validate_collection),
    doc_list: List[QADocument] = Body(description="知识内容", alias="docList"),
):
    """向知识库添加新文档"""
    logger.info(
        f"Create document of collection. Collection name: <{collection_name}>; Number of documents: <{len(doc_list)}>"
    )

    if not doc_list:
        return Error(msg="文档列表不能为空")

    try:
        response = await QAQdrantDocumentStore(index=collection_name).write_documents(
            qa_document_list=doc_list
        )

        write_docs_count = response.get("writer", {}).get("documents_written", 0) // 2
        logger.info(
            f"Document is created successfully. Collection name: <{collection_name}>; Number of writes: <{write_docs_count}>"
        )

        return Success(
            msg="知识创建成功",
            data={
                "collection_name": collection_name,
                "write_docs_count": write_docs_count,
            },
        )
    except Exception as e:
        logger.error(
            f"Document creation failed. Collection name: <{collection_name}>; Error: {str(e)}"
        )
        return Error(msg="知识创建失败", data=str(e))


@router.delete("/collection/document", summary="删除知识")
@timing_decorator
async def delete_documents(
    collection_name: str = Depends(validate_collection),
    doc_id_list: List[str] = Body(description="知识的id", alias="docIdList"),
):
    """删除知识库中的文档"""
    logger.info(
        f"Delete from documents. Collection name: <{collection_name}>; Document IDs: <{doc_id_list}>"
    )

    if not doc_id_list:
        return Error(msg="文档ID列表不能为空")

    try:
        data = QAQdrantDocumentStore(collection_name).delete_documents(doc_id_list)
        logger.info(
            f"Documents is deleted successfully. Collection name: <{collection_name}>; Document IDs: <{doc_id_list}>"
        )
        return Success(msg="删除知识成功", data=data)
    except Exception as e:
        logger.error(
            f"Documents deletion failed. Collection name: <{collection_name}>; Error: {str(e)}"
        )
        return Error(msg="删除知识失败", data=str(e))


@router.get("/query", summary="知识内容查询")
@timing_decorator
async def query_documents(
    collection_name: str = Depends(validate_collection),
    query: str = Query(description="查询内容", alias="query"),
    top_k: int = Query(
        default=5,
        ge=1,
        le=30,
        description="返回数量(1-30), 默认5",
        alias="topK",
    ),
    score_threshold: float = Query(
        default=None,
        description="分数阈值(0-1.00)，question默认0.65，qa_pair默认0.88",
        alias="scoreThreshold",
    ),
    doc_type: str = Query(
        default="qa_pair",
        description="查询类型(question, qa_pair)",
        alias="type",
    ),
):
    """
    在知识库中查询文档
    - query: 查询文本
    - type: 查询类型，question或qa_pair
    - top_k: 返回的最大结果数
    - score_threshold: 相似度分数阈值
    """
    logger.info(
        f"Query the documents of collection. Collection name: <{collection_name}>; Query: <{query}>; Top K: <{top_k}>; Score threshold: <{score_threshold}>"
    )

    # 验证查询类型
    if doc_type not in ["question", "qa_pair"]:
        return Error(msg="无效的查询类型，必须是'question'或'qa_pair'")

    # 设置默认检索阈值
    if not score_threshold:
        score_threshold = (
            CONFIG.PRECISION_THRESHOLD
            if doc_type == "question"
            else CONFIG.SCORE_THRESHOLD
        )

    try:
        # start_time = time.perf_counter()
        doc = QAQdrantDocumentStore(collection_name)
        doc_list = await doc.query(
            query=query,
            top_k=top_k,
            score_threshold=score_threshold,
            doc_type=doc_type,
        )
        # query_time = time.perf_counter() - start_time

        processed_docs = [
            {"id": doc.id, "content": doc.content, "score": doc.score}
            for doc in doc_list
        ]

        data = {
            "collection_name": collection_name,
            "doc_list": processed_docs,
            "top_k": top_k,
            "score_threshold": score_threshold,
            # "query_time_ms": round(query_time * 1000, 2),  # 转换为毫秒并保留2位小数
        }
        logger.info(
            f"Knowledge query success. Collection name: <{collection_name}>; Number of results: <{len(processed_docs)}>"
        )

        return Success(data=data)
    except Exception as e:
        logger.error(
            f"Knowledge query failure. Collection name: <{collection_name}>; Query: <{query}>; Error: {str(e)}"
        )
        return Error(msg="查询失败", data=str(e))


@router.get("/exact-query", summary="精确知识查询")
@timing_decorator
async def exact_query(
    collection_name: str = Depends(validate_collection),
    query: str = Query(description="查询内容", alias="query"),
):
    """执行精确查询，直接匹配问题后返回答案"""
    logger.info(
        f"Exact query of collection. Collection name: <{collection_name}>; Query: <{query}>"
    )

    try:

        doc_store = QAQdrantDocumentStore(collection_name)
        answer = await doc_store.query_exact(query=query)

        if answer:
            logger.info(
                f"Exact query success. Collection name: <{collection_name}>; Found answer"
            )
            return Success(
                data={
                    "collection_name": collection_name,
                    "query": query,
                    "answer": answer,
                }
            )
        else:
            logger.info(
                f"Exact query found no results. Collection name: <{collection_name}>; Query: <{query}>"
            )
            return Success(
                data={
                    "collection_name": collection_name,
                    "query": query,
                    "answer": None,
                }
            )
    except Exception as e:
        logger.error(
            f"Exact query failure. Collection name: <{collection_name}>; Query: <{query}>; Error: {str(e)}"
        )
        return Error(msg="精确查询失败", data=str(e))


@router.get("/collection/stats", summary="获取知识库统计信息")
@timing_decorator
async def get_collection_stats(
    collection_name: str = Depends(validate_collection),
):
    """获取知识库的统计信息"""
    logger.info(f"Getting stats for collection <{collection_name}>")

    try:
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
            "collection_name": collection_name,
            "total_documents": total_docs,
            "average_length": round(avg_length, 2),
        }

        logger.info(f"Stats for collection <{collection_name}> retrieved successfully")
        return Success(data=stats)
    except Exception as e:
        logger.error(
            f"Failed to get stats for collection <{collection_name}>. Error: {str(e)}"
        )
        return Error(msg="获取知识库统计信息失败", data=str(e))


@router.put("/collection/document", summary="更新知识")
@timing_decorator
async def update_document(
    collection_name: str = Depends(validate_collection),
    doc_id: str = Query(description="知识ID", alias="docId"),
    updated_content: Dict[str, Any] = Body(
        description="更新的内容", alias="updatedContent"
    ),
):
    """
    更新文档内容
    注意：这需要在QAQdrantDocumentStore中实现update_document方法
    """
    logger.info(
        f"Updating document. Collection name: <{collection_name}>; Document ID: <{doc_id}>"
    )

    # 这里假设QAQdrantDocumentStore有一个update_document方法
    # 如果没有，需要先在qdrant.py中实现该方法
    try:
        # 实际实现可能需要根据QAQdrantDocumentStore的实际功能调整
        # 这里只是提供一个接口示例
        doc_store = QAQdrantDocumentStore(collection_name)

        # 先获取文档，确认存在
        docs = doc_store.filter_documents(
            {"field": "id", "operator": "==", "value": doc_id}
        )

        if not docs:
            logger.error(
                f"Document <{doc_id}> not found in collection <{collection_name}>"
            )
            return Error(msg="文档不存在")

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

        logger.info(
            f"Document <{doc_id}> updated successfully in collection <{collection_name}>"
        )
        return Success(msg="文档更新成功", data={"doc_id": doc_id})
    except Exception as e:
        logger.error(
            f"Failed to update document <{doc_id}> in collection <{collection_name}>. Error: {str(e)}"
        )
        return Error(msg="更新文档失败", data=str(e))
