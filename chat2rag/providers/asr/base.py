from abc import ABC, abstractmethod
from typing import AsyncGenerator


class BaseASR(ABC):
    """
    语音识别的基类
    """

    def __init__(self):
        pass

    @abstractmethod
    def _initialize(self):
        """
        初始化ASR引擎
        """
        pass

    @abstractmethod
    def transcribe(self, audio_file: str) -> str:
        """
        将音频文件转换为文本"
        """
        pass

    @abstractmethod
    async def stream_transcribe(self, audio_file: str) -> AsyncGenerator[str, None]:
        """
        将音频文件转换为文本流
        """
        pass
