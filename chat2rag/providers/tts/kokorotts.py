import asyncio
import io
import logging
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Tuple

import soundfile as sf
import torch
from kokoro import KModel, KPipeline

from chat2rag.core.tts.base import BaseTTS

logger = logging.getLogger(__name__)


class KokoroTTS(BaseTTS):
    def __init__(self, speed=1.2):
        """
        使用 kokoro 进行语音合成
        Args:
            voice: 要使用的声音标识符
            language: 语言代码(例如："zh", "en")
        """
        self.speed = speed
        self.REPO_ID = "hexgrad/Kokoro-82M-v1.1-zh"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.zh_pipeline = self._initialize()

    def _initialize(self):
        """
        初始化kokoroTTS模型
        """
        logger.info("初始化kokoroTTS模型...")
        try:
            en_pipeline = KPipeline(lang_code="a", repo_id=self.REPO_ID, model=False)

            def en_callable(text):
                if text == "Kokoro":
                    return "kˈOkəɹO"
                elif text == "Sol":
                    return "sˈOl"
                return next(en_pipeline(text)).phonemes

            model = KModel(repo_id=self.REPO_ID).to(self.device).eval()

            zh_pipeline = KPipeline(
                lang_code="z",
                repo_id=self.REPO_ID,
                model=model,
                en_callable=en_callable,
            )
            return zh_pipeline
        except Exception as e:
            logger.error("初始化kokoroTTS模型失败: %s", e)
            raise

    def speak(self, text: str, voice: str = None) -> Tuple[bytes, int]:
        """
        将文本转换为语音数据

        Args:
            text: 要转换的文本

        Returns:
            语音数据的字节, 采样率
        """
        logger.info("Processing TTS segment: %s", text)
        if not voice:
            voice = "zf_001"
            logger.warning("未指定语音，使用默认语音: %s", voice)
        try:
            # 获取音频数据
            generator = self.zh_pipeline(text, voice=voice, speed=self.speed)
            result = next(generator)
            wav_tensor = result.audio
            numpy_array = wav_tensor.numpy()

            # 将音频数据转换为字节流
            wav_buffer = io.BytesIO()
            sf.write(wav_buffer, numpy_array, 24000, format="WAV")

            # 将指针移回缓冲区开始处
            wav_buffer.seek(0)
            return wav_buffer.read(), 24000

        except Exception as e:
            logger.error("文本转换语音失败: %s", e)
            raise

    async def stream_speak(self, text: str, voice: str = None) -> AsyncGenerator[bytes, None]:
        """
        异步方法：将文本转换为语音数据流

        Args:
            text: 要转换的文本

        Yields:
            语音数据的字节块
        """
        logger.info("正在将文本转换为语音数据流: %s", text)
        if not voice:
            voice = "zf_001"
            logger.warning("未指定语音，使用默认语音: %s", voice)
        try:
            # 分割文本为句子
            sentences = self._split_into_sentences(text)

            # 逐句处理
            for sentence in sentences:
                if not sentence.strip():
                    continue

                # 异步生成当前句子的音频
                loop = asyncio.get_running_loop()
                generator = await loop.run_in_executor(
                    None,
                    lambda: self.zh_pipeline(sentence, voice=voice, speed=self.speed),
                )
                result = await loop.run_in_executor(None, lambda: next(generator))
                wav_tensor = result.audio
                numpy_array = wav_tensor.numpy()

                # 转换为WAV
                wav_buffer = io.BytesIO()
                await loop.run_in_executor(None, lambda: sf.write(wav_buffer, numpy_array, 24000, format="WAV"))
                wav_buffer.seek(0)

                # 读取WAV数据
                yield wav_buffer.read(), 24000

        except Exception as e:
            logger.error("文本转换语音流失败: %s", e)
            raise

    @staticmethod
    def get_available_voices() -> List[Dict[str, Any]]:
        """
        获取可用的语音列表

        Returns:
            语音信息列表
        """
        voices_dir = Path("models") / "Kokoro-82M-v1.1-zh" / "voices"

        # 检查目录是否存在
        if not voices_dir.exists():
            print(f"目录 {voices_dir} 不存在")
            return []

        # 使用列表推导式获取所有文件名（不含后缀）
        voices = [file.stem for file in voices_dir.iterdir() if file.is_file()]

        return voices
