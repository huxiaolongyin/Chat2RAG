from fastapi import APIRouter, Query
from tortoise.expressions import Q

from chat2rag.logger import get_logger
from chat2rag.responses import Error, Success
from chat2rag.schemas.common import Current, Size
from chat2rag.schemas.sensitive import (
    SensitiveWordCategoryCreate,
    SensitiveWordCategoryUpdate,
    SensitiveWordCreate,
    SensitiveWordUpdate,
)
from chat2rag.services.sensitive_service import (
    SensitiveCategoryService,
    SensitiveService,
)

logger = get_logger(__name__)
router = APIRouter()
category_service = SensitiveCategoryService()
sensitive_service = SensitiveService()


@router.get("/category", summary="获取分类列表")
async def get_category_list(
    current: Current = 1,
    size: Size = 10,
    name_or_desc: str = Query(None, description="名称或描述", alias="nameOrDesc", max_length=10),
):
    try:
        q = Q()
        if name_or_desc:
            q &= Q(name__icontains=name_or_desc) | Q(description__icontains=name_or_desc)

        total, categorys = await category_service.get_list(current, size, q)
        return Success(
            data={
                "categoryList": [await category.to_dict() for category in categorys],
                "total": total,
                "current": current,
                "size": size,
            }
        )
    except Exception as e:
        msg = f"获取分类列表流程失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.get("/category/{category_id}", summary="获取分类详情")
async def get_category_detail(category_id: int):
    try:
        category = await category_service.get(category_id)
        if not category:
            return Error(msg="分类不存在")
        return Success(data=await category.to_dict())
    except Exception as e:
        msg = f"获取分类详情失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.post("/category", summary="创建分类")
async def create_category(category_in: SensitiveWordCategoryCreate):
    try:
        exist_category = await category_service.model.filter(name=category_in.name).first()
        if exist_category:
            return Error(msg="该分类已存在")
        category = await category_service.create(category_in)
        return Success(data=await category.to_dict())
    except Exception as e:
        msg = f"创建分类失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.put("/category/{category_id}", summary="更新分类")
async def update_category(category_id: int, category_in: SensitiveWordCategoryUpdate):
    try:
        category = await category_service.get(category_id)
        if not category:
            return Error(msg="分类数据不存在")
        exist_category = await category_service.model.filter(name=category_in.name).first()
        if exist_category:
            return Error(msg="该分类已存在")
        category = await category_service.update(category_id, category_in)
        return Success(data=await category.to_dict())
    except Exception as e:
        msg = f"更新分类失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.delete("/category/{category_id}", summary="删除分类")
async def delete_category(category_id: int):
    try:
        category = await category_service.get(category_id)
        if not category:
            return Error(msg="分类不存在")
        await category_service.remove(category_id)
        return Success(msg="删除成功")
    except Exception as e:
        msg = f"删除分类失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.get("/word", summary="获取敏感词列表")
async def get_word_list(
    current: Current = 1,
    size: Size = 10,
    word: str = Query(None, description="敏感词", max_length=50),
    category_id: int = Query(None, description="分类ID", alias="categoryId"),
    level: int = Query(None, description="级别", ge=1, le=3),
):
    try:
        q = Q()
        if word:
            q &= Q(word__icontains=word)
        if category_id:
            q &= Q(category_id=category_id)
        if level:
            q &= Q(level=level)

        total, words = await sensitive_service.get_list(current, size, q, prefetch=["category"])
        return Success(
            data={
                "wordList": [await word.to_dict() for word in words],
                "total": total,
                "current": current,
                "size": size,
            }
        )
    except Exception as e:
        msg = f"获取敏感词列表失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.post("/word", summary="创建敏感词")
async def create_word(word_in: SensitiveWordCreate):
    try:
        exist_word = await sensitive_service.model.filter(word=word_in.word).first()
        if exist_word:
            return Error(msg="该敏感词已存在")
        word = await sensitive_service.create(word_in)
        return Success(data=await word.to_dict())
    except Exception as e:
        msg = f"创建敏感词失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.put("/word/{word_id}", summary="更新敏感词")
async def update_word(word_id: int, word_in: SensitiveWordUpdate):
    try:
        word = await sensitive_service.get(word_id)
        if not word:
            return Error(msg="敏感词不存在")
        exist_word = await sensitive_service.model.filter(word=word_in.word).first()
        if exist_word:
            return Error(msg="该敏感词已存在")
        word = await sensitive_service.update(word_id, word_in)
        return Success(data=await word.to_dict())
    except Exception as e:
        msg = f"更新敏感词失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.delete("/word/{word_id}", summary="删除敏感词")
async def delete_word(word_id: int):
    try:
        word = await sensitive_service.get(word_id)
        if not word:
            return Error(msg="敏感词不存在")
        await sensitive_service.remove(word_id)
        return Success(msg="删除成功")
    except Exception as e:
        msg = f"删除敏感词失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.get("/word/{word_id}", summary="获取敏感词详情")
async def get_word_detail(word_id: int):
    try:
        word = await sensitive_service.get(word_id)
        if not word:
            return Error(msg="敏感词不存在")
        return Success(data=await word.to_dict())
    except Exception as e:
        msg = f"获取敏感词详情失败: {str(e)}"
        logger.error(msg)
        return Error(msg)
