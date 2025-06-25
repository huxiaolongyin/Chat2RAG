import numpy as np
import torch
from silero_vad import VADIterator, load_silero_vad

from chat2rag.core.vad.base import VAD
from chat2rag.logger import get_logger

logger = get_logger(__name__)


class SileroVAD(VAD):
    def __init__(self):
        # 加载模型
        self.model = load_silero_vad()
        logger.debug(f"VAD Iterator initialized with model {self.model}")

        # 加载参数，TODO：使用参数文件控制
        self.sampling_rate = 16000
        self.threshold = 0.5
        self.min_silence_duration_ms = 400

        # 当前状态
        self.vad_iterator = VADIterator(
            self.model,
            threshold=self.threshold,
            sampling_rate=self.sampling_rate,
            min_silence_duration_ms=self.min_silence_duration_ms,
        )

    @staticmethod
    def int2float(sound):
        """
        Convert int16 audio data to float32.
        """
        sound = sound.astype(np.float32) / 32768.0
        return sound

    def is_vad(self, audio_bytes: bytes):
        try:
            audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_float32 = self.int2float(audio_int16)
            tensor = torch.from_numpy(audio_float32)
            # logger.debug(
            #     # f"Tensor shape: {tensor.shape}, dtype: {tensor.dtype}, min: {tensor.min()}, max: {tensor.max()}"
            # )
            vad_output = self.vad_iterator(tensor)
            # logger.debug(f"VAD output: {vad_output}")
            if vad_output is not None:
                logger.debug(f"VAD output: {vad_output}")
            return vad_output
        except Exception as e:
            logger.error(f"Error in VAD processing: {e}")
            return None

    def reset_states(self):
        try:
            self.vad_iterator.reset_states()  # Reset model states after each audio
            logger.debug("VAD states reset.")
        except Exception as e:
            logger.error(f"Error resetting VAD states: {e}")
