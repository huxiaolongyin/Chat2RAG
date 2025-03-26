from enum import Enum
from math import ceil
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Query

from chat2rag.api.schema import Error, Success, ToolConfig
from chat2rag.logger import logger
from chat2rag.tools.tool_manager import tool_manager

router = APIRouter()
# tool_manager = ToolManager()


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class ToolSortField(str, Enum):
    TOOL_NAME = "name"
    TOOL_DESC = "description"


@router.get("/list")
async def list_tools(
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
    """
    获取工具列表
    """
    logger.info(
        f"获取工具列表。工具描述过滤: <{tool_desc}>; 当前页: {current}; 每页数量: {size}"
    )

    # 获取所有工具
    tool_list = tool_manager.tool_list

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

    # 获取总记录数
    total = len(tool_list)

    # 获取分页数据
    start_index = (current - 1) * size
    end_index = start_index + size
    records = tool_list[start_index:end_index]
    # 计算总页数
    pages = ceil(total / size)

    logger.info(f"成功获取工具列表。工具描述过滤: <{tool_desc}>; 总数: {total}")

    # 返回分页数据
    return Success(
        data={
            "tool_list": records,
            "current": current,
            "size": size,
            "total": total,
            "pages": pages,
        },
    )


@router.post("/add")
async def add_tool(tool_config: ToolConfig = Body(..., description="工具配置")):
    """
    添加新工具
    """
    logger.info(f"添加新工具。工具名称: {tool_config.function.name}")

    # 从ToolConfig中提取必要信息
    function_data = tool_config.function.model_dump()
    name = function_data.get("name")
    description = function_data.get("description", "")
    url = function_data.get("url", "")
    method = function_data.get("method", "GET")
    parameters = function_data.get("parameters", {})

    # 调用add_custom_tool方法添加工具
    success = tool_manager.add_custom_tool(
        name=name,
        description=description,
        url=url,
        method=method,
        parameters=parameters,
    )

    if success:
        logger.info(f"成功添加新工具。工具名称: {name}")
        return Success(msg="添加工具成功")

    logger.error(f"添加工具失败。工具名称: {name}")
    return Error(msg="添加失败，可能是工具名称已存在")


@router.put("/update")
async def update_tool(
    tool_name: str = Query(..., description="工具名称", alias="toolName"),
    tool_config: Dict[str, Any] = Body(..., description="工具配置更新"),
):
    """
    更新工具配置
    """
    logger.info(f"更新工具。工具名称: {tool_name}")

    # 从请求体中提取要更新的字段
    description = tool_config.get("description")
    url = tool_config.get("url")
    method = tool_config.get("method")
    parameters = tool_config.get("parameters")

    # 调用update_custom_tool方法更新工具
    success = tool_manager.update_custom_tool(
        name=tool_name,
        description=description,
        url=url,
        method=method,
        parameters=parameters,
    )

    if success:
        logger.info(f"成功更新工具。工具名称: {tool_name}")
        return Success(msg="更新成功")

    logger.error(f"更新工具失败。工具名称: {tool_name}")
    return Error(msg="更新失败，工具不存在")


@router.delete("/remove")
async def remove_tool(
    tool_name: str = Query(..., description="工具名称", alias="toolName")
):
    """
    删除工具
    """
    logger.info(f"删除工具。工具名称: {tool_name}")

    # 调用delete_custom_tool方法删除工具
    success = tool_manager.delete_custom_tool(tool_name)

    if success:
        logger.info(f"成功删除工具。工具名称: {tool_name}")
        return Success(msg="删除成功")

    logger.error(f"删除工具失败。工具名称: {tool_name}")
    return Error(msg="删除失败，找不到工具")


@router.get("/detail")
async def get_tool_detail(
    tool_name: str = Query(..., description="工具名称", alias="toolName")
):
    """
    获取工具详情
    """
    logger.info(f"获取工具详情。工具名称: {tool_name}")

    # 获取工具配置
    tool_config = tool_manager.get_custom_tool(tool_name)

    if tool_config:
        logger.info(f"成功获取工具详情。工具名称: {tool_name}")
        return Success(data=tool_config)

    logger.error(f"获取工具详情失败。工具名称: {tool_name}")
    return Error(msg="找不到工具")


@router.get("/test")
async def test_tool(
    tool_name: str = Query(..., description="工具名称", alias="toolName"),
    kwargs: str = Query(..., description="执行参数"),
):
    """
    测试工具能够正常执行
    """
    logger.info(f"测试工具。工具名称: {tool_name}; 执行参数: {kwargs}")

    # 解析执行参数
    try:
        params = eval(kwargs)
    except Exception as e:
        logger.error(f"参数解析失败: {str(e)}")
        return Error(msg=f"参数格式错误: {str(e)}")

    # 获取工具对象
    tool = tool_manager.get_tool_by_name(tool_name)

    if not tool:
        logger.error(f"工具不存在: {tool_name}")
        return Error(msg=f"找不到工具: {tool_name}")

    # 执行工具函数
    try:
        result = tool.function(**params)
        logger.info(f"成功测试工具。工具名称: {tool_name}; 执行参数: {kwargs}")
        return Success(data=result)
    except Exception as e:
        logger.error(
            f"工具执行失败。工具名称: {tool_name}; 执行参数: {kwargs}; 错误: {str(e)}"
        )
        return Error(msg=str(e))
