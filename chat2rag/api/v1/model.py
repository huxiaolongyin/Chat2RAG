from typing import List

from fastapi import APIRouter, BackgroundTasks, Query
from tortoise.expressions import Q

from chat2rag.logger import get_logger
from chat2rag.schemas.base import BaseResponse, PaginatedResponse
from chat2rag.schemas.common import Current, Size
from chat2rag.schemas.model import (
    ModelProviderCreate,
    ModelProviderData,
    ModelProviderIdData,
    ModelProviderUpdate,
    ModelSourceCreate,
    ModelSourceData,
    ModelSourceOption,
    ModelSourceUpdate,
)
from chat2rag.services.model_service import provider_service, source_service

logger = get_logger(__name__)

router = APIRouter()


@router.get("/list", response_model=BaseResponse[List[ModelSourceOption]], summary="获取模型列表", deprecated=True)
@router.get("/option", response_model=BaseResponse[List[ModelSourceOption]], summary="获取模型列表")
async def get_model_list():
    q = Q(healthy=True) & Q(enabled=True)
    _, sources = await source_service.get_list(1, 999, q)
    data = list({item.alias: ModelSourceOption(name=item.alias, id=item.alias) for item in sources}.values())
    return BaseResponse.success(data=data)


@router.get("/provider", response_model=PaginatedResponse[ModelProviderData], summary="获取模型渠道商列表")
async def get_model_providers(
    current: Current = 1,
    size: Size = 10,
    name_or_desc: str | None = Query(None, alias="nameOrDesc", max_length=50),
    enabled: bool | None = Query(None, description="是否启用"),
):
    q = Q()
    if name_or_desc:
        q &= Q(name__icontains=name_or_desc) | Q(description__icontains=name_or_desc)
    if enabled is not None:
        q &= Q(enabled=enabled)

    total, providers = await provider_service.get_list(current, size, q)
    return PaginatedResponse.create(
        items=[ModelProviderData.model_validate(item) for item in providers],
        total=total,
        current=current,
        size=size,
    )


@router.get("/provider/{provider_id}", response_model=BaseResponse[ModelProviderData], summary="获取模型渠道商详情")
async def get_model_provider_detail(provider_id: str):
    provider = await provider_service.get(provider_id)
    return BaseResponse.success(data=ModelProviderData.model_validate(provider))


@router.post("/provider", response_model=BaseResponse[ModelProviderData], summary="创建模型渠道商")
async def create_model_provider(provider_in: ModelProviderCreate, background_tasks: BackgroundTasks):
    provider = await provider_service.create(provider_in)
    if provider.enabled:
        background_tasks.add_task(provider.get_models)
    return BaseResponse.success(data=ModelProviderData.model_validate(provider))


@router.put("/provider/{provider_id}", response_model=BaseResponse[ModelProviderIdData], summary="更新模型渠道商")
async def update_model_provider(provider_id: str, provider_in: ModelProviderUpdate, background_tasks: BackgroundTasks):
    provider = await provider_service.update(provider_id, provider_in)
    if provider.enabled:
        background_tasks.add_task(provider.get_models)
    return BaseResponse.success(data=ModelProviderIdData(model_provider_id=provider.id))


@router.delete("/provider/{provider_id}", response_model=BaseResponse, summary="删除模型渠道商")
async def delete_model_provider(provider_id: str):
    # TODO: 如果有业务关联可做检查（例如关联的ModelSource）
    await provider_service.remove(provider_id)
    return BaseResponse.success(msg="删除成功")


# ==================== ModelSource APIs ====================
@router.get("/source", response_model=PaginatedResponse[ModelSourceData], summary="获取模型源列表")
async def get_model_sources(
    current: Current = 1,
    size: Size = 10,
    name_or_alias: str | None = Query(None, alias="nameOrAlias", max_length=50, description="名称或别名"),
    provider_id: int | None = Query(None, alias="providerId", description="模型供应商ID"),
    enabled: bool | None = Query(None, description="是否启用"),
    healthy: bool | None = Query(None, description="是否健康"),
):

    q = Q()
    if name_or_alias:
        q &= Q(alias__icontains=name_or_alias) | Q(name__icontains=name_or_alias)
    if provider_id:
        q &= Q(provider_id=provider_id)
    if enabled is not None:
        q &= Q(enabled=enabled)
    if healthy is not None:
        q &= Q(healthy=healthy)

    total, sources = await source_service.get_list(current, size, q)

    return PaginatedResponse.create(
        items=[ModelSourceData.model_validate(source) for source in sources],
        total=total,
        current=current,
        size=size,
    )


@router.get("/source/{source_id}", response_model=BaseResponse[ModelSourceData], summary="获取模型源详情")
async def get_model_source_detail(source_id: str):
    source = await source_service.get(source_id)
    return BaseResponse.success(ModelSourceData.model_validate(source))


@router.post("/source", response_model=BaseResponse[ModelSourceData], summary="创建模型源")
async def create_model_source(source_in: ModelSourceCreate, background_tasks: BackgroundTasks):
    source = await source_service.create(source_in)
    if source.enabled:
        background_tasks.add_task(source.update_latency)
    return BaseResponse.success(data=ModelSourceData.model_validate(source))


@router.put("/source/{source_id}", response_model=BaseResponse[ModelSourceData], summary="更新模型源")
async def update_model_source(source_id: str, source_in: ModelSourceUpdate, background_tasks: BackgroundTasks):
    source = await source_service.update(source_id, source_in)
    if source.enabled:
        background_tasks.add_task(source.update_latency)
    return BaseResponse.success(data=ModelSourceData.model_validate(source))


@router.delete("/source/{source_id}", response_model=BaseResponse, summary="删除模型源")
async def delete_model_source(source_id: str):
    await source_service.remove(source_id)
    return BaseResponse.success(msg="删除成功")
