from typing import List

from pydantic import Field

from .base import BaseSchema


class TTSRequest(BaseSchema):
    text: str = Field(..., description="要转换的文本", max_length=5000)
    voice: str = Field("longanhuan", description="语音ID")
    speed: float = Field(1.0, ge=0.5, le=2.0, description="语速")
    format: str = Field("wav", description="音频格式: wav/mp3/pcm")
    sample_rate: int = Field(24000, description="采样率")
    return_type: str = Field("base64", description="返回类型: base64/stream")


class TTSResponse(BaseSchema):
    audio: str = Field(..., description="音频数据(base64编码)")
    format: str = Field(..., description="音频格式")
    sample_rate: int = Field(..., description="采样率")


class VoiceInfo(BaseSchema):
    id: str = Field(..., description="语音ID")
    name: str = Field(..., description="语音名称")
    language: str = Field(..., description="语言")
    gender: str = Field(..., description="性别")
