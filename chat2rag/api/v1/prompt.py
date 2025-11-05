from math import ceil

from fastapi import APIRouter, Query
from tortoise.expressions import Q

from chat2rag.config import CONFIG
from chat2rag.logger import auto_log, get_logger
from chat2rag.responses import Error, Success
from chat2rag.schemas.common import Current, Size
from chat2rag.schemas.prompt import PromptCreate, PromptUpdate
from chat2rag.services.prompt_service import PromptService

logger = get_logger(__name__)

router = APIRouter()

prompt_service = PromptService()


@router.get("/", summary="获取提示词列表")
@router.get("/list", summary="获取提示词列表")
@auto_log(level="info")
async def get_prompt_list(
    current: Current = 1,
    size: Size = 10,
    prompt_name: str = Query(
        None, description="提示词名称", alias="promptName", max_length=50
    ),
    prompt_desc: str = Query(
        None, description="提示词描述", alias="promptDesc", max_length=50
    ),
):
    try:
        # 创建默认提示词
        defaul_prompt = await prompt_service.model.filter(prompt_name="默认").first()
        if not defaul_prompt:
            await prompt_service.create(
                PromptCreate(
                    promptName="默认",
                    promptDesc=f"默认",
                    promptText=CONFIG.RAG_PROMPT_TEMPLATE,
                )
            )

        q = Q()
        if prompt_name:
            q &= Q(prompt_name__icontains=prompt_name)
        if prompt_desc:
            q &= Q(prompt_desc__icontains=prompt_desc)

        total, prompts = await prompt_service.get_list(current, size, q)

        return Success(
            data={
                "promptList": [prompt for prompt in prompts],
                "total": total,
                "current": current,
                "size": size,
                "pages": ceil(total / size),
            }
        )
    except Exception as e:
        msg = f"获取提示词列表失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.get("/version", summary="设置提示词版本")
@auto_log(level="info")
async def update_version(
    prompt_id: int = Query(alias="promptId"),
    version: int = Query(),
):
    try:
        return Success(data=await prompt_service.set_version(prompt_id, version))
    except Exception as e:
        msg = f"设置提示词版本失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.get("/{prompt_id}", summary="获取提示词详情")
@auto_log(level="info")
async def get_detail(prompt_id: int):
    try:
        return Success(data=await prompt_service.get_detail(prompt_id))
    except Exception as e:
        msg = f"获取提示词详情失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.post("/", summary="添加提示词")
@router.post("/add", summary="添加提示词")
@auto_log(level="info")
async def create_prompt(prompt_in: PromptCreate):
    try:
        exist_prompt = await prompt_service.model.filter(
            prompt_name=prompt_in.prompt_name
        ).first()

        # 查看是否重名
        if exist_prompt:
            msg = "该提示词名称已存在"
            logger.warning(msg)
            return Error(msg)

        prompt = await prompt_service.create(prompt_in)
        return Success(data={"promptId": prompt.get("id")}, msg="创建提示词成功")

    except Exception as e:
        msg = f"创建提示词失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.put("/{prompt_id}", summary="更新提示词")
@router.put("/update/{prompt_id}", summary="更新提示词")
@auto_log(level="info")
async def _(prompt_id: int, prompt_in: PromptUpdate):
    try:
        # 查看是否存在分类
        prompt = await prompt_service.get(prompt_id)
        if not prompt:
            msg = "提示词不存在"
            logger.warning(msg)
            return Error(msg)

        if prompt_in.prompt_name:
            # 查看是否重名
            exist_prompt = (
                await prompt_service.model.filter(prompt_name=prompt_in.prompt_name)
                .exclude(id=prompt_id)
                .first()
            )
            if exist_prompt:
                msg = "该提示词已存在"
                logger.warning(msg)
                return Error(msg)

        prompt = await prompt_service.update(prompt_id, prompt_in)
        return Success(data={"promptId": prompt.get("id")}, msg="更新提示词成功")

    except Exception as e:
        msg = f"更新指令分类失败: {str(e)}"
        logger.error(msg)
        return Error(msg)


@router.delete("/{prompt_id}", summary="删除提示词")
@router.delete("/remove/{prompt_id}", summary="删除提示词")
@auto_log(level="info")
async def _(prompt_id: int):
    try:
        # 查看是否存在
        prompt = await prompt_service.get(prompt_id)
        if not prompt:
            msg = "提示词不存在"
            logger.warning(msg)
            return Error(msg)

        await prompt_service.remove(prompt_id)
        return Success(msg="删除提示词成功")

    except Exception as e:
        msg = f"删除提示词失败: {str(e)}"
        logger.error(msg)
        return Error(msg)
