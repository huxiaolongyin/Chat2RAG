from math import ceil
from typing import Literal, Optional

from fastapi import APIRouter, Body, Query
from tortoise.expressions import Q

from chat2rag.enums import SortOrder, ToolSortField
from chat2rag.logger import auto_log, get_logger
from chat2rag.models import MCPTool
from chat2rag.responses import Error, Success
from chat2rag.schemas.common import Current, Size
from chat2rag.schemas.tools import (
    APIToolCreateRequest,
    APIToolUpdateRequest,
    CombinedCreateRequest,
    CombinedUpdateRequest,
    MCPServerCreateRequest,
    MCPServerUpdateRequest,
)
from chat2rag.services.tool_service import api_service, mcp_service

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", summary="获取工具列表")
@router.get("/list", summary="获取工具列表")  # TODO: 将要移除
@auto_log(level="info")
async def get_tool_list(
    current: Current = 1,
    size: Size = 10,
    tool_type: Optional[Literal["api", "mcp", "all"]] = Query(
        "all", description="工具类型", alias="toolType"
    ),
    tool_name: Optional[str] = Query(None, description="工具名称", alias="toolName"),
    tool_desc: Optional[str] = Query(None, description="工具描述", alias="toolDesc"),
    is_active: Optional[bool] = Query(None, description="是否启用", alias="isActive"),
    sort_by: Optional[ToolSortField] = Query(
        ToolSortField.CREATE_TIME, description="排序字段", alias="sortBy"
    ),
    sort_order: Optional[SortOrder] = Query(
        SortOrder.DESC, description="排序方向(asc, desc)，默认 desc", alias="sortOrder"
    ),
):
    # 构建查询条件
    q = Q()
    if tool_name:
        q &= Q(name__icontains=tool_name)
    if tool_desc:
        q &= Q(description__icontains=tool_desc)
    if is_active is not None:
        q &= Q(is_active=is_active)

    tool_list = []
    total = 0

    # 构建排序
    order_prefix = "-" if sort_order == SortOrder.DESC else ""
    order = [f"{order_prefix}{sort_by.value}"]

    if tool_type in ["api", "all"]:
        # 获取API工具
        api_total, api_tools = await api_service.get_list(1, 999, q, order)
        tool_list.extend(
            [{**await tool.to_dict(), "tool_type": "api"} for tool in api_tools]
        )
        total += api_total

    if tool_type in ["mcp", "all"]:
        # 获取MCP工具
        mcp_total, mcp_tools = await mcp_service.get_mcp_tool_list(1, 999, q, order)
        tool_list.extend(
            [{**await tool.to_dict(), "tool_type": "mcp"} for tool in mcp_tools]
        )
        total += mcp_total

    # 如果是获取全部工具，需要重新排序和分页
    if tool_type == "all":
        # 合并后重新排序
        sort_key = sort_by.value
        tool_list.sort(
            key=lambda x: x.get(sort_key, ""), reverse=(sort_order == SortOrder.DESC)
        )

        # 重新分页
        start_idx = (current - 1) * size
        end_idx = start_idx + size
        tool_list = tool_list[start_idx:end_idx]

    return Success(
        data={
            "tool_list": tool_list,
            "current": current,
            "size": size,
            "total": total,
            "pages": ceil(total / size),
        },
    )


@router.post("/", summary="创建工具")
@router.post("/add", summary="创建工具")  # TODO: 将要移除
@auto_log(level="info")
async def create_tool(request: CombinedCreateRequest):
    if isinstance(request, APIToolCreateRequest):
        existing_api_tool = await api_service.model.filter(
            name=request.data.name
        ).first()
        if existing_api_tool:
            msg = "工具名已存在"
            logger.warning(msg)
            return Error(msg)

        api_tool = await api_service.create(request.data)
        return Success(msg="API工具创建成功", data=await api_tool.to_dict())

    elif isinstance(request, MCPServerCreateRequest):
        existing_mcp_tool = await mcp_service.model.filter(
            name=request.data.name
        ).first()
        if existing_mcp_tool:
            msg = "工具名已存在"
            logger.warning(msg)
            return Error(msg)

        mcp_tool = await mcp_service.create(request.data)
        return Success(msg="MCP工具创建成功", data=await mcp_tool.to_dict())

    return Error(msg="入参格式不正确")


@router.put("/{tool_id}", summary="更新工具")
@router.put("/update/{tool_id}", summary="更新工具")  # TODO: 将要移除
@auto_log(level="info")
async def update_tool(
    tool_id: int,
    tool_type: Literal["api", "mcp"] = Query(
        ..., alias="toolType", description="工具类型"
    ),
    request: CombinedUpdateRequest = Body(...),
):
    """更新工具信息"""
    if tool_type == "api":
        if not isinstance(request, APIToolUpdateRequest):
            return Error(msg="工具类型与请求数据不匹配")

        tool = await api_service.get(tool_id)
        if not tool:
            return Error(msg="工具不存在")
        # 检查名称是否已被其他工具使用
        if request.data.name:
            existing = (
                await api_service.model.filter(name=request.data.name)
                .exclude(id=tool_id)
                .first()
            )
            if existing:
                return Error(msg="工具名已存在")

        api_tool = await api_service.update(tool_id, request.data)
        if not api_tool:
            return Error(msg="工具不存在")

        return Success(msg="API工具更新成功", data=await api_tool.to_dict())

    elif tool_type == "mcp":
        if not isinstance(request, MCPServerUpdateRequest):
            return Error(msg="工具类型与请求数据不匹配")

        tool = await mcp_service.get(tool_id)
        if not tool:
            return Error(msg="工具不存在")
        # 检查名称是否已被其他工具使用
        if request.data.name:
            existing = (
                await mcp_service.model.filter(name=request.data.name)
                .exclude(id=tool_id)
                .first()
            )
            if existing:
                return Error(msg="工具名已存在")

        mcp_tool = await mcp_service.update(tool_id, request.data)
        if not mcp_tool:
            return Error(msg="工具不存在")

        return Success(msg="MCP服务器更新成功", data=await mcp_tool.to_dict())

    return Error(msg="不支持的工具类型")


@router.get("/{tool_id}", summary="获取工具详情")
@router.get("/detail/{tool_id}", summary="获取工具详情")
@auto_log(level="info")
async def get_tool_detail(
    tool_id: int,
    tool_type: Literal["api", "mcp"] = Query(
        ..., alias="toolType", description="工具类型"
    ),
):
    """获取工具详细信息"""
    if tool_type == "api":
        tool = await api_service.get(tool_id)
        if not tool:
            return Error(msg="API工具不存在")
        return Success(data={**await tool.to_dict(), "tool_type": "api"})

    elif tool_type == "mcp":
        tool = await MCPTool.filter(id=tool_id).prefetch_related("server").first()
        if not tool:
            return Error(msg="MCP工具不存在")

        server = tool.server

        return Success(
            data={
                **await server.to_dict(),
                "toolType": "mcp",
                "tool": await tool.to_dict(),
            }
        )

    return Error(msg="不支持的工具类型")


@router.delete("/{tool_id}", summary="删除工具")
@router.delete("/remove/{tool_id}", summary="删除工具")
@auto_log(level="info")
async def remove_tool(
    tool_id: int,
    tool_type: Literal["api", "mcp"] = Query(
        ..., alias="toolType", description="工具类型"
    ),
):
    if tool_type == "api":
        if not await api_service.get(tool_id):
            return Error("工具不存在")
        await api_service.remove(tool_id)
    else:
        if not await mcp_service.get(tool_id):
            return Error("MCP服务不存在")
        await mcp_service.remove(tool_id)
    return Success(msg="删除工具成功")


@router.post("/{server_id}/sync", summary="同步MCP工具")
@auto_log(level="info")
async def sync_mcp_tools(server_id: int):
    """手动同步MCP服务器的工具列表"""
    try:
        if not await mcp_service.get(server_id):
            return Error("工具不存在")
        tools = await mcp_service.sync_tools(server_id)

        if tools is None:
            return Error(msg="MCP服务器不存在")

        return Success(
            msg=f"成功同步 {len(tools)} 个工具",
            data={
                "serverId": server_id,
                "toolCount": len(tools),
                "tools": [await tool.to_dict() for tool in tools],
            },
        )
    except Exception as e:
        logger.error(f"同步MCP工具失败: {e}")
        return Error(msg=f"同步失败: {str(e)}")
