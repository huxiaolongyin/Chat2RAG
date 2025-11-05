from fastapi import APIRouter

from chat2rag.config import CONFIG
from chat2rag.logger import auto_log
from chat2rag.responses import Success

router = APIRouter()


@router.get("/list", summary="获取模型列表")
@auto_log(level="info")
def get_model_list():
    """
    获取模型列表
    """
    return Success(data=CONFIG.MODEL_LIST)
