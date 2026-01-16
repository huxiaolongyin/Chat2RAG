from fastapi import APIRouter, Query
from tortoise.expressions import Q

from chat2rag.core.logger import get_logger
from chat2rag.schemas.base import BaseResponse, PaginatedResponse
from chat2rag.schemas.common import Current, Size
from chat2rag.schemas.sensitive import (
    SensitiveWordCategoryCreate,
    SensitiveWordCategoryData,
    SensitiveWordCategoryUpdate,
    SensitiveWordCreate,
    SensitiveWordData,
    SensitiveWordUpdate,
)
from chat2rag.services.sensitive_service import (
    sensitive_category_service,
    sensitive_service,
)

logger = get_logger(__name__)
router = APIRouter()


@router.get("/category", response_model=PaginatedResponse[SensitiveWordCategoryData], summary="获取分类列表")
async def get_category_list(
    current: Current = 1,
    size: Size = 10,
    name_or_desc: str = Query(None, description="名称或描述", alias="nameOrDesc", max_length=10),
):
    q = Q()
    if name_or_desc:
        q &= Q(name__icontains=name_or_desc) | Q(description__icontains=name_or_desc)

    total, categorys = await sensitive_category_service.get_list(current, size, q)

    return PaginatedResponse.create(
        items=[SensitiveWordCategoryData.model_validate(category) for category in categorys],
        total=total,
        current=current,
        size=size,
    )


@router.get("/category/{category_id}", response_model=BaseResponse[SensitiveWordCategoryData], summary="获取分类详情")
async def get_category_detail(category_id: int):
    category = await sensitive_category_service.get(category_id)
    return BaseResponse.success(data=SensitiveWordCategoryData.model_validate(category))


@router.post("/category", response_model=BaseResponse[SensitiveWordCategoryData], summary="创建分类")
async def create_category(category_in: SensitiveWordCategoryCreate):
    category = await sensitive_category_service.create(category_in)
    return BaseResponse.success(data=SensitiveWordCategoryData.model_validate(category))


@router.put("/category/{category_id}", response_model=BaseResponse[SensitiveWordCategoryData], summary="更新分类")
async def update_category(category_id: int, category_in: SensitiveWordCategoryUpdate):
    category = await sensitive_category_service.update(category_id, category_in)
    return BaseResponse.success(data=SensitiveWordCategoryData.model_validate(category))


@router.delete("/category/{category_id}", response_model=BaseResponse, summary="删除分类")
async def delete_category(category_id: int):
    await sensitive_category_service.remove(category_id)
    return BaseResponse.success(msg="删除成功")


@router.get("/word", response_model=PaginatedResponse[SensitiveWordData], summary="获取敏感词列表")
async def get_word_list(
    current: Current = 1,
    size: Size = 10,
    word: str = Query(None, description="敏感词", max_length=50),
    category_id: int = Query(None, description="分类ID", alias="categoryId"),
    level: int = Query(None, description="级别", ge=1, le=3),
):

    q = Q()
    if word:
        q &= Q(word__icontains=word)
    if category_id:
        q &= Q(category_id=category_id)
    if level:
        q &= Q(level=level)

    total, words = await sensitive_service.get_list(current, size, q, prefetch=["category"])
    return PaginatedResponse.create(
        items=[SensitiveWordData.model_validate(word) for word in words], total=total, current=current, size=size
    )


@router.post("/word", response_model=BaseResponse[SensitiveWordData], summary="创建敏感词")
async def create_word(word_in: SensitiveWordCreate):
    word = await sensitive_service.create(word_in)
    return BaseResponse.success(data=SensitiveWordData.model_validate(word))


@router.put("/word/{word_id}", response_model=BaseResponse[SensitiveWordData], summary="更新敏感词")
async def update_word(word_id: int, word_in: SensitiveWordUpdate):
    word = await sensitive_service.update(word_id, word_in)
    return BaseResponse.success(data=SensitiveWordData.model_validate(word))


@router.delete("/word/{word_id}", response_model=BaseResponse, summary="删除敏感词")
async def delete_word(word_id: int):
    await sensitive_service.remove(word_id)
    return BaseResponse.success(msg="删除成功")


@router.get("/word/{word_id}", response_model=BaseResponse[SensitiveWordData], summary="获取敏感词详情")
async def get_word_detail(word_id: int):

    word = await sensitive_service.get(word_id)
    return BaseResponse.success(data=SensitiveWordData.model_validate(word))
