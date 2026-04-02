from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Tuple, Union


class BaseTTS(ABC):
    """文本到语音转换的基类"""

    def __init__(self, audio_config):
        self.voice: str = audio_config.voice
        self.language = audio_config.language
        self.format: str = audio_config.format
        self.sample_rate: int = audio_config.sample_rate
        self.speed: float = audio_config.speed
        self._initialize()

    @abstractmethod
    def _initialize(self):
        pass

    def speak(self, text: str, voice: str = None) -> Tuple[bytes, int]:
        """
        同步方法：将文本转换为语音数据

        Args:
            text: 要转换的文本
            voice: 语音ID（可选）

        Returns:
            语音数据的字节, 采样率
        """
        raise NotImplementedError("This TTS engine does not support synchronous speak")

    async def stream_speak(self, text: str, voice: str = None) -> AsyncGenerator[Tuple[bytes, int], None]:
        """
        异步方法：将文本转换为语音数据流

        Args:
            text: 要转换的文本
            voice: 语音ID（可选）

        Yields:
            语音数据的字节块, 采样率
        """
        raise NotImplementedError("This TTS engine does not support stream_speak")
        yield

    async def connect(self):
        """建立实时 TTS 连接（用于流式实时合成）"""
        raise NotImplementedError("This TTS engine does not support realtime connection")

    async def append_text(self, text: str):
        """流式追加文本到 TTS"""
        raise NotImplementedError("This TTS engine does not support append_text")

    async def finish_text(self):
        """完成文本输入"""
        raise NotImplementedError("This TTS engine does not support finish_text")

    async def get_audio(self) -> AsyncGenerator[bytes | None, None]:
        """获取音频流"""
        raise NotImplementedError("This TTS engine does not support get_audio")
        yield

    async def get_audio_nowait(self) -> bytes | None:
        """非阻塞获取音频"""
        raise NotImplementedError("This TTS engine does not support get_audio_nowait")

    async def close(self):
        """关闭 TTS 连接"""
        raise NotImplementedError("This TTS engine does not support close")

    def is_realtime(self) -> bool:
        """判断是否为实时 TTS"""
        try:
            self.connect.__func__
            return True
        except AttributeError:
            return False

    def _split_into_sentences(self, text: str) -> List[str]:
        import re

        return re.split(r"([。！？!?.])", text)

    def speak_to_file(self, text: str, filename: Union[str, Path], voice: str = None) -> str:
        audio_data, _ = self.speak(text, voice)
        path = Path(filename)
        path.write_bytes(audio_data)
        return str(path.absolute())

    async def stream_speak_to_file(self, text: str, filename: Union[str, Path]) -> str:
        pass

    def set_voice(self, voice: str):
        self.voice = voice

    def set_language(self, language: str):
        self.language = language

    @abstractmethod
    def get_available_voices(self) -> List[Dict[str, Any]]:
        pass

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(voice={self.voice}, language={self.language})"
