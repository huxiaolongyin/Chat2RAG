import requests
from fastapi import APIRouter

from chat2rag.api.schema import Error, Success
from chat2rag.config import CONFIG

router = APIRouter()


@router.get("/list", summary="获取模型列表")
def get_model_list():
    """
    获取模型列表
    """
    return Success(data=CONFIG.MODEL_LIST)
    # else:
    #     return Error(msg="获取模型列表失败", data=response.json())
