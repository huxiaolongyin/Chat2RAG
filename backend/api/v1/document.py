from fastapi import APIRouter, Query, Body
from rag_core.document.qdrant import QdrantDocumentManage
from backend.schema import Success, Error
from typing import Union, Optional
from math import ceil
from enum import Enum
from rag_core.utils.logger import logger

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
    """获取知识库列表，并判断知识库是否存在"""
    if collection_name not in QdrantDocumentManage().get_collection_names():
        return False
    return True


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
        f"获取知识库列表中，知识库索引：{collection_name}；页码：{current}；每页数量：{size}；"
    )

    # 获取所有数据
    collection_list = QdrantDocumentManage().get_collections()

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

    logger.info(f"获取知识库列表成功，知识库索引：{collection_name}；总数={total}；")

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
    logger.info(f"创建知识库中，知识库索引：{collection_name}；")

    if collection_exists(collection_name):
        logger.error(f"知识库已存在，知识库索引：{collection_name}；")
        return Error(msg="知识库已存在", data={"collection_name": collection_name})
    if QdrantDocumentManage(collection_name).create:
        logger.info(f"知识库创建成功，知识库索引：{collection_name}；")
        return Success(msg="知识库创建成功", data={"collection_name": collection_name})
    else:
        logger.error(f"知识库创建失败，知识库索引：{collection_name}；")
        return Error(msg="知识库创建失败", data={"collection_name": collection_name})


@router.delete("/collection", summary="删除知识库")
async def _(
    collection_name: str = Query(description="知识库名称", alias="collectionName")
):
    if not collection_exists(collection_name):
        logger.error(f"知识库不存在，知识库索引：{collection_name}；")
        return Error(msg="知识库不存在")
    try:
        QdrantDocumentManage(collection_name).delete_collection
        logger.info(f"知识库删除成功，知识库索引：{collection_name}；")
        return Success(msg="删除知识库成功", data={"collection_name": collection_name})
    except Exception as e:
        logger.error(
            f"知识库删除失败，知识库索引：{collection_name}； 错误: {str(e)}；"
        )
        return Error(msg="删除知识库失败", data=str(e))


@router.get("/collection/document", summary="获取知识库所有文档")
async def _(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    current: int = Query(1, ge=1, description="当前页码，默认1"),
    size: int = Query(10, ge=1, le=100, description="每页数量(1-100)，默认10"),
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
        f"获取知识库文档，知识库索引：{collection_name}； 页码：{current}；每页数量：{size}；"
    )
    if not collection_exists(collection_name):
        logger.error(f"知识库不存在，知识库索引：{collection_name}；")
        return Error(msg="知识库不存在")
    document_list = QdrantDocumentManage(collection_name).get_document_list
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

    logger.info(f"获取文档成功，知识库索引：{collection_name}； 总数：{total}；")

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


@router.post(
    "/collection/document",
    summary="创建知识，写入时会占满CPU，建议一次50条以内；",
)
async def _(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    doc_list: Union[list, str] = Body(description="知识内容", alias="docList"),
):
    doc_len = len(doc_list if isinstance(doc_list, list) else [doc_list])
    logger.info(f"创建知识中，知识库索引：{collection_name}；文档数量：{doc_len}；")
    if not collection_exists(collection_name):
        logger.error(f"知识创建失败，知识库不存在，知识库索引：{collection_name}；")
        return Error(msg="知识库不存在")
    if isinstance(doc_list, str):
        doc_list = [doc_list]
    try:
        response = await QdrantDocumentManage(index=collection_name).write_documents(
            collection=collection_name, documents=doc_list
        )

        write_docs_count = response.get("writer").get("documents_written")
        logger.info(
            f"知识创建成功，知识库索引：{collection_name}；写入数量：{write_docs_count}；"
        )
        return Success(
            msg="知识创建成功",
            data={
                "collection_name": collection_name,
                "write_docs_count": write_docs_count,
            },
        )
    except Exception as e:
        logger.error(f"知识创建失败，知识库索引：{collection_name}； 错误: {str(e)}；")
        return Error(msg="知识创建失败", data=str(e))


@router.delete("/collection/document", summary="删除知识")
async def _(
    collection_name: str = Query(description="知识库名称", alias="collectionName"),
    doc_id_list: Union[list, str] = Body(description="知识的id", alias="docIdList"),
):
    logger.info(f"删除知识中: 知识库索引：{collection_name}；文档ID：{doc_id_list}；")

    if not collection_exists(collection_name):
        logger.error(f"知识库不存在，知识库索引：{collection_name}；")
        return Error(msg="知识库不存在")
    if isinstance(doc_id_list, str):
        doc_id_list = [doc_id_list]
    try:
        data = QdrantDocumentManage(collection_name).delete_documents(doc_id_list)
        logger.info(
            f"知识删除成功，知识库索引：{collection_name}；文档ID：{doc_id_list}；"
        )
        return Success(msg="删除知识成功", data=data)
    except Exception as e:
        logger.error(f"知识删除失败，知识库索引：{collection_name}；错误: {str(e)}；")
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
):

    # profiler = Profiler()
    # profiler.start()
    logger.info(
        f"知识库查询中，知识库索引：{collection_name}；查询内容：{query}；返回数量：{top_k}；分数阈值：{score_threshold}；"
    )

    if not collection_exists(collection_name):
        logger.error(f"知识库不存在，知识库索引：{collection_name}；")
        return Error(msg="知识库不存在")
    doc = QdrantDocumentManage(collection_name)
    try:
        response = await doc.query(
            query=query, top_k=top_k, score_threshold=score_threshold
        )

        doc_list = response.get("retriever").get("documents")

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
            f"查询成功: 知识库索引：{collection_name}；结果数量：{len(processed_docs)}；"
        )

        # profiler.stop()
        # print(profiler.output_text(unicode=True, color=True))

        return Success(data=data)
    except Exception as e:
        logger.error(
            f"知识查询失败，知识库索引：{collection_name}；查询内容：{query}；错误: {str(e)}；"
        )
        return Error(msg="查询失败", data=str(e))
