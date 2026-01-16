from typing import Literal

from fastapi import APIRouter, Body, Depends, Query
from tortoise.expressions import Q

from chat2rag.core.enums import SortOrder, ToolType
from chat2rag.core.logger import get_logger
from chat2rag.schemas.base import BaseResponse, PaginatedResponse
from chat2rag.schemas.tools import (
    CombinedCreateRequest,
    CombinedUpdateRequest,
    ToolData,
    ToolQueryParams,
    ToolSyncData,
)
from chat2rag.services.tool_service import mcp_service, tool_service

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=PaginatedResponse[ToolData], summary="获取工具列表")
@router.get("/list", response_model=PaginatedResponse[ToolData], summary="获取工具列表", deprecated=True)
async def get_tool_list(params: ToolQueryParams = Depends()):
    # 构建查询条件
    q = Q()
    if params.tool_name:
        q &= Q(name__icontains=params.tool_name)
    if params.tool_desc:
        q &= Q(description__icontains=params.tool_desc)
    if params.is_active is not None:
        q &= Q(is_active=params.is_active)

    # 构建排序（如果是desc，则添加负号“-”）
    order = [f"{'-' if params.sort_order == SortOrder.DESC else ''}{params.sort_by}"]

    total, tool_list = await tool_service.get_list(params.current, params.size, params.tool_type, q, order)

    return PaginatedResponse.create(
        items=[ToolData.model_validate(tool) for tool in tool_list],
        current=params.current,
        size=params.size,
        total=total,
    )


@router.post("", response_model=BaseResponse[ToolData], summary="创建工具")
@router.post("/add", response_model=BaseResponse[ToolData], summary="创建工具", deprecated=True)
async def create_tool(request: CombinedCreateRequest):
    tool = await tool_service.create(request)
    tool_dict = {**tool.__dict__, "tool_type": request.tool_type}
    return BaseResponse.success(data=ToolData.model_validate(tool_dict), msg="工具创建成功")


@router.put("/{tool_id}", response_model=BaseResponse[ToolData], summary="更新工具")
@router.put("/update/{tool_id}", response_model=BaseResponse[ToolData], summary="更新工具", deprecated=True)
async def update_tool(
    tool_id: int,
    tool_type: Literal["api", "mcp"] = Query(..., alias="toolType", description="工具类型"),
    request: CombinedUpdateRequest = Body(...),
):
    tool = await tool_service.update(tool_id, tool_type, request)
    tool_dict = {**tool.__dict__, "tool_type": request.tool_type}
    return BaseResponse.success(data=ToolData.model_validate(tool_dict), msg="工具更新成功")


@router.get("/{tool_id}", response_model=BaseResponse[ToolData], summary="获取工具详情")
@router.get("/detail/{tool_id}", response_model=BaseResponse[ToolData], summary="获取工具详情", deprecated=True)
async def get_tool_detail(
    tool_id: int,
    tool_type: Literal["api", "mcp"] = Query(..., alias="toolType", description="工具类型"),
):
    tool = await tool_service.get(tool_id, tool_type)
    tool_dict = {**tool.__dict__, "tool_type": tool_type}
    return BaseResponse.success(data=ToolData.model_validate(tool_dict), msg="工具获取成功")


@router.delete("/{tool_id}", response_model=BaseResponse, summary="删除工具")
@router.delete("/remove/{tool_id}", response_model=BaseResponse, summary="删除工具", deprecated=True)
async def remove_tool(
    tool_id: int,
    tool_type: Literal["api", "mcp"] = Query(..., alias="toolType", description="工具类型"),
):
    await tool_service.remove(tool_id, tool_type)
    return BaseResponse.success(msg="删除工具成功")


@router.post("/{server_id}/sync", response_model=BaseResponse[ToolSyncData], summary="手动同步MCP工具")
async def sync_mcp_tools(server_id: int):
    tool_objs = await mcp_service.sync_tools(server_id)
    tools = []
    for obj in tool_objs:
        tool_dict = {**obj.__dict__, "tool_type": ToolType.MCP}
        tools.append(ToolData.model_validate(tool_dict))

    return BaseResponse.success(
        msg=f"成功同步 {len(tools)} 个工具", data=ToolSyncData(server_id=server_id, tool_count=len(tools), tools=tools)
    )
