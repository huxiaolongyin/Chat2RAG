from math import ceil

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from backend.schema import Error, Success
from backend.schema.prompt import PromptCreate
from rag_core.database.database import get_db
from rag_core.database.models import Prompt
from rag_core.logging import logger

router = APIRouter()


@router.get("/list")
def _(
    current: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    prompt_name: str = Query(
        None,
        description="提示词名称",
        alias="promptName",
    ),
    prompt_desc: str = Query(
        None,
        description="提示词描述",
        alias="promptDesc",
    ),
    db: Session = Depends(get_db),
):
    """
    Get prompt list
    """
    # 构建查询
    query = db.query(Prompt)

    # 添加搜索条件
    if prompt_name:
        query = query.filter(Prompt.prompt_name.ilike(f"%{prompt_name}%"))
    if prompt_desc:
        query = query.filter(Prompt.prompt_text.ilike(f"%{prompt_desc}%"))

    # 计算偏移量
    offset = (current - 1) * size

    # 获取总记录数
    total = query.count()

    # 获取分页数据
    records = [prompt.to_dict() for prompt in query.offset(offset).limit(size).all()]

    # 计算总页数
    pages = ceil(total / size)

    logger.info(
        f"Getting prompt list successfully. Prompt name: <{prompt_name}>; Prompt desc: <{prompt_desc}>; Total: {total}"
    )

    # 返回分页数据
    return Success(
        data={
            "prompt_list": records,
            "current": current,
            "size": size,
            "total": total,
            "pages": pages,
        },
    )


@router.post("/add")
def _(
    prompt: PromptCreate,
    db: Session = Depends(get_db),
):
    # 检查名称是否已存在
    existing_prompt = (
        db.query(Prompt).filter(Prompt.prompt_name == prompt.prompt_name).first()
    )

    if existing_prompt:
        logger.warning(f"Prompt name already exists: {prompt.prompt_name}")
        return Error(msg="提示词名称已存在")

    # 创建新提示词
    db_prompt = Prompt(**prompt.model_dump())
    db.add(db_prompt)
    db.commit()
    db.refresh(db_prompt)
    if not db_prompt:
        logger.error(f"Add new prompt falied. Prompt name: {prompt.prompt_name}")
        return Error(msg="添加失败")

    logger.info(f"Add new prompt successfully. Prompt name: {prompt.prompt_name}")
    return Success(msg="添加提示词成功")


@router.put("/update")
def _(
    prompt_id: int = Query(alias="promptId"),
    prompt: PromptCreate = Body(...),
    db: Session = Depends(get_db),
):
    db_prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if db_prompt is None:
        logger.error(f"Update prompt falied. Prompt id: {prompt_id}")
        return Error(msg="提示词未找到")

    for key, value in prompt.model_dump().items():
        setattr(db_prompt, key, value)

    db.commit()
    db.refresh(db_prompt)
    logger.info(f"Update prompt successfully. Prompt id: {prompt_id}")
    return Success(msg="更新提示词成功")


@router.delete("/remove")
def _(
    prompt_id: int = Query(..., alias="promptId"),
    db: Session = Depends(get_db),
):
    db_prompt = db.query(Prompt).filter(Prompt.id == prompt_id).first()
    if db_prompt is None:
        logger.error(f"Update prompt falied. Prompt id: {prompt_id}")
        return Error(msg="提示词未找到")

    db.delete(db_prompt)
    db.commit()
    logger.info(f"Delete prompt successfully. Prompt id: {prompt_id}")
    return Success(msg="删除成功")
