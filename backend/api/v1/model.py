import requests
from fastapi import APIRouter

from backend.schema import Error, Success
from rag_core.config import CONFIG

router = APIRouter()


@router.get("/list", summary="获取模型列表")
def _():
    """
    获取模型列表
    """
    response = requests.get(
        f"{CONFIG.OPENAI_BASE_URL}/models",
        headers={"Authorization": "Bearer " + CONFIG.OPENAI_API_KEY},
    )
    print({"Authorization": "Bearer " + CONFIG.OPENAI_API_KEY})
    if response.status_code == 200:
        return Success(data=response.json()["data"])
    else:
        return Error(msg="获取模型列表失败", data=response.json())
