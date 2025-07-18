import copy
from datetime import datetime
from math import ceil
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from chat2rag.api.schema import Error, Success, ToolConfig
from chat2rag.database.connection import get_db
from chat2rag.database.models import CustomTool
from chat2rag.enums import SortOrder, ToolSortField, ToolType
from chat2rag.logger import get_logger
from chat2rag.tools.tool_manager import tool_manager
from chat2rag.utils.short_name import ai_create_shortname

logger = get_logger(__name__)

router = APIRouter()


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
    db: Session = Depends(get_db),
):
    """
    Get the list of tools
    """
    logger.info(
        f"Get the list of tools. Tool Description Filtering: <{tool_desc}>; Current Page: {current}; Page Size: {size}"
    )

    # Get all tools
    api_tools = db.query(CustomTool).filter(CustomTool.type == ToolType.API).all()
    mcp_tools = db.query(CustomTool).filter(CustomTool.type != ToolType.API).all()

    tool_list = []
    for tool in api_tools:
        tool_list.append(
            {
                "type": tool.type,
                "function": {
                    "name": tool.name,
                    "display_name": tool.display_name,
                    "description": tool.description,
                    "url": tool.url,
                    "method": tool.method.value,
                    "parameters": tool.parameters,
                    "command": tool.command,
                    "status": tool.status.value,
                },
            }
        )

    for tool in mcp_tools:
        try:
            tool_list.extend(
                [
                    {
                        "type": tool.type.value,
                        "mcp_name": tool.name,
                        "function": {
                            "name": key,
                            "display_name": values.get("name"),
                            "description": values.get("description"),
                            "url": tool.url,
                            "method": tool.method.value,
                            "parameters": values.get("properties"),
                            "command": tool.command,
                            "status": tool.status.value,
                        },
                    }
                    for key, values in tool.customization.items()
                ]
            )
        except Exception as e:
            logger.error(f"Error occurred while processing MCP tools: {e}")

    if tool_desc:
        tool_list = [
            tool
            for tool in tool_list
            if tool_desc in tool.get("description", "").lower()
        ]

    # Obtain the total number of records
    total = len(tool_list)

    # Sorting logic
    if sort_by and tool_list:
        # 定义排序键映射
        sort_key_mapping = {
            ToolSortField.TOOL_NAME: "name",
            ToolSortField.TOOL_DESC: "description",
            # Add more fields if needed
        }

        sort_key = sort_key_mapping.get(sort_by, "name")
        reverse = sort_order == SortOrder.DESC

        # 执行排序
        tool_list.sort(
            key=lambda x: x.get(sort_key, "").lower(), reverse=reverse  # 忽略大小写排序
        )

    # 计算总页数
    start_index = (current - 1) * size
    end_index = start_index + size
    pages = ceil(total / size)

    logger.info(
        f"Successfully obtained the list of tools. Tool Description Filtering: <{tool_desc}>; Total: {total}"
    )

    # 返回分页数据
    return Success(
        data={
            "tool_list": tool_list[start_index:end_index],
            "current": current,
            "size": size,
            "total": total,
            "pages": pages,
        },
    )


@router.post("/add")
async def add_tool(
    tool_config: ToolConfig = Body(..., description="工具配置"),
    db: Session = Depends(get_db),
):
    """
    Add new tools
    """
    try:
        funciton = tool_config.function

        logger.info(f"Adding a new tool. Tool Name: {funciton.name}")

        # Check if the tool name already exists
        existing_tool = (
            db.query(CustomTool).filter(CustomTool.name == funciton.name).first()
        )

        if existing_tool:
            logger.warning(f"Tool name already exists: {funciton.name}")
            return Error(
                msg=f"Failed to add tool. Tool name '{funciton.name}' already exists"
            )

        # Extract the necessary information from the MCP Tool Config
        tool_data = funciton.model_dump()

        # Create a tool instance
        tool = CustomTool(**tool_data)

        # Obtain the list of tool names from MCP and set the custom information
        if tool.type != ToolType.API:
            try:
                customization = {}
                for t in tool._fetch_mcp_tools().tools:
                    short_name = await ai_create_shortname(t.description)
                    customization[t.name] = {
                        "name": short_name,
                        "description": t.description,
                        "properties": t.parameters,
                    }
                tool.customization = customization
            except Exception as e:
                logger.warning(f"Error setting customization: {e}")
                tool.customization = {}

        db.add(tool)
        db.commit()
        db.refresh(tool)

        logger.info(f"成功添加新工具。工具名称: {tool_config.function.name}")
        return Success(msg="添加工具成功")

    except Exception as e:
        # Rollback the transaction
        db.rollback()
        error_msg = f"Error occurred while adding tool: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return Error(msg=error_msg)


@router.put("/update")
async def update_tool(
    tool_name: str = Query(..., description="工具名称", alias="toolName"),
    tool_config: Dict[str, Any] = Body(..., description="工具配置更新"),
    db: Session = Depends(get_db),
):
    """
    Update an existing tool's configuration

    Args:
        tool_name: The name of the tool to update
        tool_config: A dictionary containing the fields to update
        db: The database session

    Returns:
        Success or Error response indicating the result of the update operation
    """
    try:
        logger.info(f"Updating tool: {tool_name}")

        # Find the tool to update
        tool = db.query(CustomTool).filter(CustomTool.name == tool_name).first()
        if not tool:
            logger.warning(f"Tool does not exist: {tool_name}")
            return Error(
                msg=f"Failed to update tool. Tool '{tool_name}' does not exist"
            )

        # If updating the tool name, check if the new name already exists
        if "name" in tool_config and tool_config["name"] != tool_name:
            existing = (
                db.query(CustomTool)
                .filter(CustomTool.name == tool_config["name"])
                .first()
            )
            if existing:
                logger.warning(f"Tool name already exists: {tool_config['name']}")
                return Error(
                    msg=f"Failed to update tool. Tool name '{tool_config['name']}' is already in use"
                )

        # Update tool attributes
        updated_fields = []
        for key, value in tool_config.items():
            if hasattr(tool, key) and key != "id":  # Prevent the update of ID
                setattr(tool, key, value)
                updated_fields.append(key)

        # If no fields were updated, return a message
        if not updated_fields:
            logger.info(f"No fields need to be updated: {tool_name}")
            return Success(msg="No fields need to be updated")

        # Save the updated tool
        tool.update_time = datetime.now()  # Timestamp for update time
        db.commit()

        logger.info(
            f"Successfully updated the tool: {tool.name}, updated fields: {', '.join(updated_fields)}"
        )
        return Success(
            msg="更新工具成功",
            data={"id": tool.id, "name": tool.name, "updated_fields": updated_fields},
        )

    except Exception as e:
        # 回滚事务
        db.rollback()
        error_msg = f"An error occurred when updating the tool: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return Error(msg=error_msg)


@router.delete("/remove")
async def remove_tool(
    tool_name: str = Query(..., description="工具名称", alias="toolName"),
    db: Session = Depends(get_db),
):
    """
    Delete the existing tools

    Args:
        tool_name: The name of the tool to delete
        db: The database session

    Returns:
        The response indicating success or failure of the deletion
    """
    try:
        logger.info(f"Deleting tool: {tool_name}")

        # Find the tool to delete
        tool = db.query(CustomTool).filter(CustomTool.name == tool_name).first()
        if not tool:
            logger.warning(f"Tool does not exist: {tool_name}")
            return Error(
                msg=f"Failed to delete tool. Tool '{tool_name}' does not exist"
            )

        # Save the tool ID for logging
        tool_id = tool.id

        # Delete the tool
        db.delete(tool)
        db.commit()

        logger.info(f"Successfully deleted the tool. ID: {tool_id}, Name: {tool_name}")
        return Success(
            msg="Successfully deleted the tool.",
            data={"id": tool_id, "name": tool_name},
        )

    except Exception as e:
        # 回滚事务
        db.rollback()
        error_msg = f"An error occurred when deleting the tool: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return Error(msg=error_msg)


@router.get("/detail")
async def get_tool_detail(
    tool_name: str = Query(..., description="工具名称", alias="toolName")
):
    """
    Get the details of the tool
    """
    logger.info(f"Getting tool detail. Tool name: {tool_name}")

    # 获取工具配置
    tool = tool_manager.fetch_tools([tool_name])[0]

    if tool:
        tool_detail = {
            "type": ToolType.STREAMABLE.value,
            "function": {
                "name": tool.name,
                "description": tool.description,
                "url": "",
                "method": "",
                "parameters": tool.parameters,
            },
        }
        logger.info(f"Successfully retrieved the tool detail. Tool name: {tool_name}")
        return Success(data=tool_detail)

    logger.error(f"Failed to retrieve the tool detail. Tool name: {tool_name}")
    return Error(msg="Failed to retrieve the tool detail")


@router.get("/refresh")
async def refresh_tools(
    id: int = Query(),
    db: Session = Depends(get_db),
):
    """
    刷新 MCP 服务的工具集
    """
    logger.info(f"Refreshing tools. Tool ID: {id}")
    tool = db.query(CustomTool).filter(CustomTool.id == id).first()

    if not tool:
        return Error(msg="Tool not found")

    if tool.type == ToolType.API.value:
        return Error(msg="API tool does not support refresh")

    customization = copy.deepcopy(tool.customization) or {}
    try:
        # 获取新工具列表
        new_tools = tool._fetch_mcp_tools().tools
        new_tool_names = {t.name for t in new_tools}

        # 1. 删除：移除不再存在的旧工具
        obsolete_tools = [
            name for name in customization.keys() if name not in new_tool_names
        ]
        for name in obsolete_tools:
            customization.pop(name)

        # 2 & 3. 新增和更新：处理新工具列表
        for t in new_tools:
            # 如果是新工具或需要获取中文短名的情况
            if (
                t.name not in customization
                or customization[t.name].get("name") == t.name
            ):
                # 获取中文短名
                short_name = await ai_create_shortname(t.description)
                customization[t.name] = {
                    "name": short_name,
                    "description": t.description,
                    "properties": t.parameters,
                }
            else:
                # 仅更新描述和参数，保留现有的自定义名称
                customization[t.name].update(
                    {
                        "description": t.description,
                        "properties": t.parameters,
                    }
                )

        tool.customization = customization
        # Save the updated tool
        tool.update_time = datetime.now()  # Timestamp for update time
        # db.merge(tool)
        db.commit()
        db.refresh(tool)
        logger.info(f"Tool customization after update: {tool.customization}")

    except Exception as e:
        logger.warning(f"Error setting customization: {e}")
        db.rollback()

    logger.info(f"Successfully refreshed the tools.")
    return Success(msg="Successfully refreshed the tools.")


# @router.get("/test")
# async def test_tool(
#     tool_name: str = Query(..., description="工具名称", alias="toolName"),
#     kwargs: str = Query(..., description="执行参数"),
# ):
#     """
#     测试工具能够正常执行
#     """
#     logger.info(f"测试工具。工具名称: {tool_name}; 执行参数: {kwargs}")

#     # 解析执行参数
#     try:
#         params = eval(kwargs)
#     except Exception as e:
#         logger.error(f"参数解析失败: {str(e)}")
#         return Error(msg=f"参数格式错误: {str(e)}")

#     # 获取工具对象
#     tool = tool_manager.get_tool_by_name(tool_name)

#     if not tool:
#         logger.error(f"工具不存在: {tool_name}")
#         return Error(msg=f"找不到工具: {tool_name}")

#     # 执行工具函数
#     try:
#         result = tool.function(**params)
#         logger.info(f"成功测试工具。工具名称: {tool_name}; 执行参数: {kwargs}")
#         return Success(data=result)
#     except Exception as e:
#         logger.error(
#             f"工具执行失败。工具名称: {tool_name}; 执行参数: {kwargs}; 错误: {str(e)}"
#         )
#         return Error(msg=str(e))
