from typing import Optional

from fastapi import APIRouter, Query
from tortoise.expressions import Q

from chat2rag.config import CONFIG
from chat2rag.logger import auto_log, get_logger
from chat2rag.responses import Error, Success
from chat2rag.schemas.common import Current, Size
from chat2rag.schemas.model import (
    ModelProviderCreate,
    ModelProviderUpdate,
    ModelSourceCreate,
    ModelSourceUpdate,
)
from chat2rag.services.model_service import ModelProviderService, ModelSourceService

logger = get_logger(__name__)

router = APIRouter()
provider_service = ModelProviderService()
source_service = ModelSourceService()


@router.get("/list", summary="获取模型列表")
@auto_log(level="info")
def get_model_list():
    """
    获取模型列表
    """
    return Success(data=CONFIG.MODEL_LIST)


@router.get("/provider", summary="获取模型渠道商列表")
@auto_log(level="info")
async def get_model_providers(
    current: Current = 1,
    size: Size = 10,
    name_or_desc: Optional[str] = Query(None, alias="nameOrDesc", max_length=50),
    enabled: Optional[bool] = Query(None, description="是否启用"),
):
    try:
        q = Q()
        if name_or_desc:
            q &= Q(name__icontains=name_or_desc) | Q(
                description__icontains=name_or_desc
            )
        if enabled is not None:
            q &= Q(enabled=enabled)

        total, providers = await provider_service.get_list(current, size, q)
        return Success(
            data={
                "providerList": [await p.to_dict() for p in providers],
                "total": total,
                "current": current,
                "size": size,
            }
        )
    except Exception as e:
        msg = f"获取模型渠道商列表失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.get("/provider/{provider_id}", summary="获取模型渠道商详情")
@auto_log(level="info")
async def get_model_provider_detail(provider_id: str):
    try:
        provider = await provider_service.get(provider_id)
        if not provider:
            msg = "模型渠道商不存在"
            logger.warning(msg)
            return Error(msg)
        return Success(data=await provider.to_dict())
    except Exception as e:
        msg = f"获取模型渠道商详情失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.post("/provider", summary="创建模型渠道商")
@auto_log(level="info")
async def create_model_provider(provider_in: ModelProviderCreate):
    try:
        exist = await provider_service.model.filter(name=provider_in.name).first()
        if exist:
            return Error(msg="该模型渠道商名称已存在")
        provider = await provider_service.create(provider_in)
        return Success(data=await provider.to_dict())
    except Exception as e:
        msg = f"创建模型渠道商失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.put("/provider/{provider_id}", summary="更新模型渠道商")
@auto_log(level="info")
async def update_model_provider(provider_id: str, provider_in: ModelProviderUpdate):
    try:
        provider = await provider_service.get(provider_id)
        if not provider:
            return Error(msg="模型渠道商不存在")
        # 校验重名
        if provider_in.name:
            exist = (
                await provider_service.model.filter(name=provider_in.name)
                .exclude(id=provider_id)
                .first()
            )
            if exist:
                return Error(msg="该模型渠道商名称已存在")
        updated = await provider_service.update(provider_id, provider_in)
        return Success(data={"providerId": updated.id}, msg="更新成功")
    except Exception as e:
        msg = f"更新模型渠道商失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.delete("/provider/{provider_id}", summary="删除模型渠道商")
@auto_log(level="info")
async def delete_model_provider(provider_id: str):
    try:
        provider = await provider_service.get(provider_id)
        if not provider:
            return Error(msg="模型渠道商不存在")
        # TODO: 如果有业务关联可做检查（例如关联的ModelSource）
        await provider_service.remove(provider_id)
        return Success(msg="删除成功")
    except Exception as e:
        msg = f"删除模型渠道商失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


# ==================== ModelSource APIs ====================
@router.get("/source", summary="获取模型源列表")
@auto_log(level="info")
async def get_model_sources(
    current: Current = 1,
    size: Size = 10,
    name_or_alias: Optional[str] = Query(None, alias="nameOrAlias", max_length=50),
    enabled: Optional[bool] = Query(None, description="是否启用"),
    healthy: Optional[bool] = Query(None, description="是否健康"),
):
    try:
        q = Q()
        if name_or_alias:
            q &= Q(alias__icontains=name_or_alias) | Q(name__icontains=name_or_alias)
        if enabled is not None:
            q &= Q(enabled=enabled)
        if healthy is not None:
            q &= Q(healthy=healthy)

        total, sources = await source_service.get_list(current, size, q)
        return Success(
            data={
                "sourceList": [await s.to_dict() for s in sources],
                "total": total,
                "current": current,
                "size": size,
            }
        )
    except Exception as e:
        msg = f"获取模型源列表失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.get("/source/{source_id}", summary="获取模型源详情")
@auto_log(level="info")
async def get_model_source_detail(source_id: str):
    try:
        source = await source_service.get(source_id)
        if not source:
            return Error(msg="模型源不存在")
        return Success(data=await source.to_dict())
    except Exception as e:
        msg = f"获取模型源详情失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.post("/source", summary="创建模型源")
@auto_log(level="info")
async def create_model_source(source_in: ModelSourceCreate):
    try:
        source = await source_service.create(source_in)
        return Success(data=await source.to_dict())
    except Exception as e:
        msg = f"创建模型源失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.put("/source/{source_id}", summary="更新模型源")
@auto_log(level="info")
async def update_model_source(source_id: str, source_in: ModelSourceUpdate):
    try:
        source = await source_service.get(source_id)
        if not source:
            return Error(msg="模型源不存在")
        updated = await source_service.update(source_id, source_in)
        return Success(data=await updated.to_dict())
    except Exception as e:
        msg = f"更新模型源失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.delete("/source/{source_id}", summary="删除模型源")
@auto_log(level="info")
async def delete_model_source(source_id: str):
    try:
        source = await source_service.get(source_id)
        if not source:
            return Error(msg="模型源不存在")
        await source_service.remove(source_id)
        return Success(msg="删除成功")
    except Exception as e:
        msg = f"删除模型源失败: {str(e)}"
        logger.error(msg)
        return Error(msg)
