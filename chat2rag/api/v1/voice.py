"""
记录用户可选的语音列表
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/list")
def get_voices():
    """获取语音列表"""
    pass


@router.get("/tts")
async def tts():
    pass


@router.get("/asr")
async def asr():
    """
    进行语音识别
    """
    pass
