from enum import Enum
from math import ceil
from typing import List, Optional

from fastapi import APIRouter, Body, Query

from backend.schema import Error, Success
from rag_core.dataclass.document import QADocument
from rag_core.document.qdrant import QAQdrantDocumentStore
from rag_core.logging import logger

# from pyinstrument import Profiler

router = APIRouter()

# 定义缓存key常量, 适用于Redis/Memcached
# collection_CACHE_KEY = "collection_list"
# DOC_CACEH_KEY = "doc_list"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class CollectionSortField(str, Enum):
    COLLECTION_NAME = "collection_name"
    DOCUMENT_COUNT = "document_count"


class DocumentSortField(str, Enum):
    DOCUMENT_CONTENT = "content"


def collection_exists(collection_name: str):
    """
    Judge the collection is already exists
    """
    if collection_name in QAQdrantDocumentStore().get_collection_names():
        return True
    return False


@router.get("/collection", summary="获取知识库列表")
async def _(
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
    # 打印日志
    logger.info(
        f"Getting the list of collections. Collection name: <{collection_name}>; Current: <{current}>; Page size: <{size}>"
    )

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

    logger.info(
        f"The list of knowledge collections is successfully obtained. Collection name: <{collection_name}>; Total: <{total}>;"
    )

    # 返回分页数据
    return Success(
        data={
            "collection_list": collection_list[start_index:end_index],
            "current": current,
            "size": size,
            "total": total,
            "pages": ceil(total / size),
        },
    )


@router.post("/collection", summary="创建新的知识库")
async def _(
    collection_name: str = Query(
        description="知识库名称",
        alias="collectionName",
    ),
):
    logger.info(
        f"Creating a knowledge collection. Collection name: <{collection_name}>"
    )

    if collection_exists(collection_name):
        logger.error(f"The knowledge collection <{collection_name}> already exists.")

        return Error(msg="知识库已存在", data={"collection_name": collection_name})

    if QAQdrantDocumentStore(collection_name).create:
        logger.info(
            f"The knowledge collection <{collection_name}> is created successfully."
        )

        return Success(msg="知识库创建成功", data={"collection_name": collection_name})
    else:
        logger.error(f"Failed to create the knowledge collection <{collection_name}>.")

        return Error(msg="知识库创建失败", data={"collection_name": collection_name})


@router.delete("/collection", summary="删除知识库")
async def _(
    collection_name: str = Query(description="知识库名称", alias="collectionName")
):
    if not collection_exists(collection_name):
        logger.error(f"Knowledge collection <{collection_name}> does not exist.")

        return Error(msg="知识库不存在")
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
async def _(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
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
    logger.info(
        f"Get documents of collection. Collection name: <{collection_name}>; Current: <{current}>; Page size: <{size}>"
    )
    if not collection_exists(collection_name):
        logger.error(f"Knowledge collection <{collection_name}> does not exist.")
        return Error(msg="知识库不存在")
    document_list = QAQdrantDocumentStore(collection_name).get_document_list
    # 如果有搜索条件则过滤
    if document_content:
        document_list = [
            doc
            for doc in document_list
            if document_content.lower() in doc["content"].lower()
        ]

    # 排序
    document_list.sort(key=lambda x: x[sort_by], reverse=(sort_order == SortOrder.DESC))

    # 计算分页
    total = len(document_list)
    start_index = (current - 1) * size
    end_index = start_index + size

    logger.info(
        f"The documents of collection is successfully obtained. Collection name: <{collection_name}>; Total: <{total}>;"
    )

    # 返回分页数据
    return Success(
        data={
            "doc_list": document_list[start_index:end_index],
            "current": current,
            "size": size,
            "total": total,
            "pages": ceil(total / size),
        },
    )


@router.post("/collection/document", summary="创建知识")
async def _(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    doc_list: List[QADocument] = Body(description="知识内容", alias="docList"),
):
    logger.info(
        f"Create document of collection. Collection name: <{collection_name}>; Number of documents: <{len(doc_list)}>"
    )

    if not collection_exists(collection_name):
        logger.error(
            f"Document creation failure, Knowledge collection <{collection_name}> does not exist."
        )

        return Error(msg="知识库不存在")

    # Soon to be deprecated
    # if isinstance(doc_list, list) and all(isinstance(x, str) for x in doc_list):
    #     doc_list = [QADocumentModel(question="", answer=doc) for doc in doc_list]
    try:
        response = await QAQdrantDocumentStore(index=collection_name).write_documents(
            qa_document_list=doc_list
        )

        write_docs_count = response.get("writer").get("documents_written") // 2
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
async def _(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    doc_id_list: List[str] = Body(description="知识的id", alias="docIdList"),
):
    logger.info(
        f"Delete from documents. Collection name: <{collection_name}>; Document IDs: <{doc_id_list}>"
    )

    if not collection_exists(collection_name):
        logger.error(f"Knowledge collection <{collection_name}> does not exist.")

        return Error(msg="知识库不存在")

    # if isinstance(doc_id_list, str):
    #     doc_id_list = [doc_id_list]
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
async def _(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    query: str = Query(description="查询内容", alias="query"),
    top_k: int = Query(
        default=5,
        ge=1,
        le=30,
        description="返回数量(1-30), 默认5",
        alias="topK",
    ),
    score_threshold: float = Query(
        default=0.6,
        description="分数阈值(0-1.00)，默认0.6",
        alias="scoreThreshold",
    ),
    type: str = Query(
        default="qa_pair",
        description="查询类型(question, qa_pair)",
        alias="type",
    ),
):

    # profiler = Profiler()
    # profiler.start()
    logger.info(
        f"Query the documents of collection. Collection name: <{collection_name}>; Query: <{query}>; Top K: <{top_k}>; Score threshold: <{score_threshold}>"
    )

    if not collection_exists(collection_name):
        logger.error(f"Knowledge collection <{collection_name}> does not exist.")

        return Error(msg="知识库不存在")

    doc = QAQdrantDocumentStore(collection_name)
    try:
        doc_list = await doc.query(
            query=query,
            top_k=top_k,
            score_threshold=score_threshold,
            type=type,
        )

        processed_docs = [
            {"id": doc.id, "content": doc.content, "score": doc.score}
            for doc in doc_list
        ]

        data = {
            "collection_name": collection_name,
            "doc_list": processed_docs,
            "top_k": top_k,
            "score_threshold": score_threshold,
        }
        logger.info(
            f"Knowledge query success. Collection name: <{collection_name}>; Number of results: <{len(processed_docs)}>"
        )

        # profiler.stop()
        # print(profiler.output_text(unicode=True, color=True))

        return Success(data=data)
    except Exception as e:
        logger.error(
            f"Knowledge query failure. Collection name: <{collection_name}>; Query: <{query}>; Error: {str(e)}"
        )
        return Error(msg="查询失败", data=str(e))
