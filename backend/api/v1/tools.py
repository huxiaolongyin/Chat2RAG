import json
from fastapi import APIRouter, Query, Body
from backend.schema import Success, Error, ToolConfig
from rag_core.tools.tool_manage import ToolManager
from rag_core.utils.logger import logger
from typing import Optional
from enum import Enum
from math import ceil

router = APIRouter()
tool_manager = ToolManager()


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class ToolSortField(str, Enum):
    TOOL_NAME = "name"
    TOOL_DESC = "description"


@router.get("/list")
async def _(
    current: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页数量"),
    tool_desc: Optional[str] = Query(
        None,
        description="工具描述",
        alias="toolDesc",
    ),
    sort_by: Optional[ToolSortField] = Query(
        ToolSortField.TOOL_NAME,
        description="排序字段",
        alias="sortBy",
    ),
    sort_order: Optional[SortOrder] = Query(
        SortOrder.DESC,
        description="排序方向(asc, desc)，默认 desc",
        alias="sortOrder",
    ),
):
    """获取所有工具列表"""
    logger.info(
        f"获取工具列表中, 工具描述：{tool_desc}；页码：{current}；每页数量：{size}；"
    )
    tool_list = tool_manager.get_all_tools()

    # 如果有搜索条件则过滤
    if tool_desc:
        tool_list = [
            tool
            for tool in tool_list
            if tool_desc.lower() in tool["function"]["description"].lower()
        ]

    # 排序
    tool_list.sort(
        key=lambda x: x["function"][sort_by], reverse=(sort_order == SortOrder.DESC)
    )

    # 计算分页
    total = len(tool_list)
    start_index = (current - 1) * size
    end_index = start_index + size

    logger.info(f"获取工具列表成功，工具描述：{tool_desc}；总数：{total}；")

    # 返回分页数据
    return Success(
        data={
            "tool_list": tool_list[start_index:end_index],
            "current": current,
            "size": size,
            "total": total,
            "pages": ceil(total / size),
        },
    )


@router.post("/add")
async def _(tool_config: ToolConfig = Body(..., description="工具配置")):
    """添加新工具"""
    logger.info(f"添加新工具，工具名称：{tool_config.function.name}；")
    success = tool_manager.add_api_tool(tool_config.model_dump())
    if success:
        logger.info(f"添加工具成功，工具名称：{tool_config.function.name}；")
        return Success(msg="添加工具成功")
    logger.error(f"添加工具失败，工具名称：{tool_config.function.name}；")
    return Error(msg="添加失败")


@router.delete("/remove")
async def _(tool_name: str = Query(..., description="q ", alias="toolName")):
    """删除工具"""
    logger.info(f"删除工具，工具名称：{tool_name}；")
    success = tool_manager.remove_api_tool(tool_name)
    if success:
        logger.info(f"删除工具成功，工具名称：{tool_name}；")
        return Success(msg="删除成功")
    logger.error(f"删除工具失败，工具名称：{tool_name}；")
    return Error(msg="找不到工具")


@router.get("/test")
async def _(
    tool_name: str = Query(..., description="工具名称", alias="toolName"),
    kwargs: str = Query(..., description="执行参数"),
):
    """测试工具能够正常执行"""
    logger.info(f"测试工具，工具名称：{tool_name}；执行参数：{kwargs}；")
    kwargs = eval(kwargs)
    try:
        result = tool_manager.execute_function(tool_name, **kwargs)
        return Success(data=result)
    except Exception as e:
        return Error(msg=str(e))


# @router.post("/execute")
# async def _(
#     tool_name: str = Query(..., description="工具名称", alias="toolName"),
#     parameters: Dict = Body(..., description="执行参数"),
# ):
#     """执行工具"""
#     result = tool_manager.execute_function(tool_name, **parameters)
#     if "error" in result:
#         return Error(message=result["error"])
#     return Success(data=result)
