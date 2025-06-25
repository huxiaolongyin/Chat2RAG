from datetime import datetime
from enum import Enum
from math import ceil
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from chat2rag.api.schema import Error, Success, ToolConfig
from chat2rag.core.database import CustomTool, get_db
from chat2rag.core.database.enums import ToolType
from chat2rag.logger import logger
from chat2rag.tools.tool_manager import tool_manager

router = APIRouter()


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
    db: Session = Depends(get_db),
):
    """
    获取工具列表
    """
    logger.info(
        f"获取工具列表。工具描述过滤: <{tool_desc}>; 当前页: {current}; 每页数量: {size}"
    )

    # 获取所有工具
    tool_list = db.query(CustomTool).filter(CustomTool.name.like(f"%{tool_desc}%"))

    # 获取总记录数
    total = tool_list.count()

    tool_list_offset = (
        tool_list.order_by(
            getattr(CustomTool, sort_by.value).desc()
            if sort_order == SortOrder.DESC
            else getattr(CustomTool, sort_by.value).asc()
        )
        .limit(size)
        .offset((current - 1) * size)
        .all()
    )
    tool_list = []
    for tool in tool_list_offset:
        if tool.type == ToolType.API:
            tool_list.append(tool.to_dict())

        else:
            tool_list.extend(tool.to_dict())

    # 计算总页数
    pages = ceil(total / size)

    logger.info(f"成功获取工具列表。工具描述过滤: <{tool_desc}>; 总数: {total}")

    # 返回分页数据
    return Success(
        data={
            "tool_list": tool_list,
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
    添加新工具
    """
    try:
        funciton = tool_config.function

        logger.info(f"添加新工具。工具名称: {funciton.name}")

        # 检查工具名称是否已存在
        existing_tool = (
            db.query(CustomTool).filter(CustomTool.name == funciton.name).first()
        )

        if existing_tool:
            logger.warning(f"工具名称已存在: {funciton.name}")
            return Error(msg=f"添加失败，工具名称 '{funciton.name}' 已存在")

        # 从MCPToolConfig中提取必要信息
        tool_data = funciton.model_dump()

        # 创建工具实例
        tool = CustomTool(**tool_data)

        db.add(tool)
        db.commit()
        db.refresh(tool)

        logger.info(f"成功添加新工具。工具名称: {tool_config.function.name}")
        return Success(msg="添加工具成功")

    except Exception as e:
        # 回滚事务
        db.rollback()
        error_msg = f"添加工具时发生错误: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return Error(msg=error_msg)


@router.put("/update")
async def update_tool(
    tool_name: str = Query(..., description="工具名称", alias="toolName"),
    tool_config: Dict[str, Any] = Body(..., description="工具配置更新"),
    db: Session = Depends(get_db),
):
    """
    更新已存在的工具配置

    Args:
        tool_name: 要更新的工具名称
        tool_config: 包含更新字段的字典
        db: 数据库会话

    Returns:
        更新成功或失败的响应
    """
    try:
        logger.info(f"更新工具: {tool_name}")

        # 查找要更新的工具
        tool = db.query(CustomTool).filter(CustomTool.name == tool_name).first()
        if not tool:
            logger.warning(f"工具不存在: {tool_name}")
            return Error(msg=f"更新失败，工具 '{tool_name}' 不存在")

        # 若更新工具名称，需检查新名称是否已存在
        if "name" in tool_config and tool_config["name"] != tool_name:
            existing = (
                db.query(CustomTool)
                .filter(CustomTool.name == tool_config["name"])
                .first()
            )
            if existing:
                logger.warning(f"工具名称已存在: {tool_config['name']}")
                return Error(msg=f"更新失败，工具名称 '{tool_config['name']}' 已被使用")

        # 更新工具属性
        updated_fields = []
        for key, value in tool_config.items():
            if hasattr(tool, key) and key != "id":  # 防止更新ID
                setattr(tool, key, value)
                updated_fields.append(key)

        # 如果没有字段被更新，返回提示
        if not updated_fields:
            logger.info(f"没有字段需要更新: {tool_name}")
            return Success(msg="没有字段需要更新")

        # 保存更新
        tool.update_time = datetime.now()  # 更新时间戳
        db.commit()

        logger.info(f"成功更新工具: {tool.name}，更新字段: {', '.join(updated_fields)}")
        return Success(
            msg="更新工具成功",
            data={"id": tool.id, "name": tool.name, "updated_fields": updated_fields},
        )

    except Exception as e:
        # 回滚事务
        db.rollback()
        error_msg = f"更新工具时发生错误: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return Error(msg=error_msg)


@router.delete("/remove")
async def remove_tool(
    tool_name: str = Query(..., description="工具名称", alias="toolName"),
    db: Session = Depends(get_db),
):
    """
    删除已存在的工具

    Args:
        tool_name: 要删除的工具名称
        db: 数据库会话

    Returns:
        删除成功或失败的响应
    """
    try:
        logger.info(f"删除工具: {tool_name}")

        # 查找要删除的工具
        tool = db.query(CustomTool).filter(CustomTool.name == tool_name).first()
        if not tool:
            logger.warning(f"工具不存在: {tool_name}")
            return Error(msg=f"删除失败，工具 '{tool_name}' 不存在")

        # 保存工具ID用于日志记录
        tool_id = tool.id

        # 删除工具
        db.delete(tool)
        db.commit()

        logger.info(f"成功删除工具。ID: {tool_id}, 名称: {tool_name}")
        return Success(msg="删除工具成功", data={"id": tool_id, "name": tool_name})

    except Exception as e:
        # 回滚事务
        db.rollback()
        error_msg = f"删除工具时发生错误: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return Error(msg=error_msg)


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
