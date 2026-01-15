from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union


class BaseTTS(ABC):
    """文本到语音转换的基类"""

    def __init__(
        self, voice: Optional[str] = None, language: str = "zh", speed: float = 1.0
    ):
        """
        初始化TTS引擎

        Args:
            voice: 要使用的声音标识符
            language: 语言代码(例如："zh", "en")
        """
        self.voice = voice
        self.language = language
        self.speed = speed
        self._initialize()

    @abstractmethod
    def _initialize(self):
        """
        初始化TTS引擎
        """
        pass

    @abstractmethod
    def speak(self, text: str) -> Tuple[bytes, int]:
        """
        同步方法：将文本转换为语音数据

        Args:
            text: 要转换的文本

        Returns:
            语音数据的字节, 采样率
        """
        pass

    @abstractmethod
    async def stream_speak(self, text: str) -> AsyncGenerator[Tuple[bytes, int], None]:
        """
        异步方法：将文本转换为语音数据流

        Args:
            text: 要转换的文本

        Yields:
            语音数据的字节块
        """
        pass

    def _split_into_sentences(self, text: str) -> List[str]:
        """将文本分割为句子"""
        # 简单的句子分割，可根据需要改进
        import re

        return re.split(r"([。！？!?.])", text)

    def speak_to_file(self, text: str, filename: Union[str, Path]) -> str:
        """
        将文本转换为语音并保存到文件(同步版本)

        Args:
            text: 要转换的文本
            filename: 保存音频的文件路径

        Returns:
            保存的文件的绝对路径
        """
        audio_data, _ = self.speak(text)
        path = Path(filename)
        path.write_bytes(audio_data)
        return str(path.absolute())

    async def stream_speak_to_file(self, text: str, filename: Union[str, Path]) -> str:
        """
        异步流式方法：使用wave模块拼接WAV文件
        """
        # TODO: 使用wave模块拼接WAV文件
        pass

    def set_voice(self, voice: str):
        """
        设置要使用的语音

        Args:
            voice: 语音ID或名称
        """
        self.voice = voice

    def set_language(self, language: str):
        """
        设置语言

        Args:
            language: 语言代码
        """
        self.language = language

    @abstractmethod
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        获取可用的语音列表

        Returns:
            语音信息列表
        """
        pass

    def __str__(self) -> str:
        """返回TTS引擎的字符串表示"""
        return (
            f"{self.__class__.__name__}(voice={self.voice}, language={self.language})"
        )
