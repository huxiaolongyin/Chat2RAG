from fastapi import APIRouter, Path, Query
from tortoise.expressions import Q

from chat2rag.logger import auto_log, get_logger
from chat2rag.schemas.base import BaseResponse
from chat2rag.schemas.common import Current, Size
from chat2rag.schemas.prompt import (
    PromptCreate,
    PromptIdResponse,
    PromptItemResponse,
    PromptPaginatedData,
    PromptUpdate,
)
from chat2rag.services.prompt_service import prompt_service
from chat2rag.utils.decorators import exception_handler

logger = get_logger(__name__)

router = APIRouter()


# fmt: off
@router.get("/list", response_model=BaseResponse[PromptPaginatedData], summary="获取提示词列表", deprecated=True)
@router.get("", response_model=BaseResponse[PromptPaginatedData], summary="获取提示词列表")
@auto_log(level="info")
@exception_handler
async def get_prompt_list(
    current: Current = 1,
    size: Size = 10,
    prompt_name: str = Query(
        None,
        description="提示词名称",
        alias="promptName",
        max_length=50,
        pattern=r"^[a-zA-Z0-9\u4e00-\u9fa5_-]+$",
    ),
    prompt_desc: str = Query(
        None,
        description="提示词描述",
        alias="promptDesc",
        max_length=200,
        pattern=r"^[a-zA-Z0-9\u4e00-\u9fa5_-]+$",
    ),
):
    q = Q()
    if prompt_name:
        q &= Q(prompt_name__icontains=prompt_name)
    if prompt_desc:
        q &= Q(versions__prompt_desc__icontains=prompt_desc)

    total, prompts = await prompt_service.get_list(current, size, q)
    data = PromptPaginatedData.create(
        items=prompts, total=total, current=current, size=size
    )
    return BaseResponse.success(data=data)


@router.get("/version", response_model=BaseResponse[PromptItemResponse], summary="设置指定提示词的活跃版本")
@auto_log(level="info")
@exception_handler
async def update_version(
    prompt_id: int = Query(alias="promptId"),
    version: int = Query(),
):
    result = await prompt_service.set_version(prompt_id, version)
    return BaseResponse.success(data=result, msg="版本设置成功")


@router.get("/{prompt_id}", response_model=BaseResponse[PromptItemResponse], summary="获取提示词详情")
@auto_log(level="info")
@exception_handler
async def get_detail(prompt_id: int = Path(..., gt=0, description="提示词ID")):
    prompt = await prompt_service.get_version(prompt_id)
    return BaseResponse.success(data=prompt)


@router.post("/add", response_model=BaseResponse[PromptIdResponse], summary="添加提示词", deprecated=True)
@router.post("", response_model=BaseResponse[PromptIdResponse], summary="添加提示词")
@auto_log(level="info")
@exception_handler
async def create_prompt(prompt_in: PromptCreate):
    prompt = await prompt_service.create(prompt_in)
    
    return BaseResponse.success(data=PromptIdResponse(prompt_id = prompt.id), msg="提示词创建成功")


@router.put("/update/{prompt_id}", response_model=BaseResponse[PromptIdResponse], summary="更新提示词",  deprecated=True)
@router.put("/{prompt_id}", response_model=BaseResponse[PromptIdResponse], summary="更新提示词")
@auto_log(level="info")
@exception_handler
async def update_prompt(prompt_id: int, prompt_in: PromptUpdate):
    prompt = await prompt_service.update(prompt_id, prompt_in)
    return BaseResponse.success(data=PromptIdResponse(prompt_id = prompt.id), msg="提示词更新成功")


@router.delete("/remove/{prompt_id}", response_model=BaseResponse, summary="删除提示词", deprecated=True)
@router.delete("/{prompt_id}", response_model=BaseResponse, summary="删除提示词")
@auto_log(level="info")
@exception_handler
async def delete_prompt(prompt_id: int):
    await prompt_service.remove(prompt_id)
    return BaseResponse.success(msg="提示词删除成功")
