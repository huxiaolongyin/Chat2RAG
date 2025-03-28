import time

import soundfile as sf
import torch
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess

from chat2rag.core.asr.base import BaseASR
from chat2rag.logger import get_logger

logger = get_logger(__name__)


class FunASR(BaseASR):
    def __init__(self):
        self.chunk_size = [0, 10, 5]
        self.encoder_chunk_look_back = 4
        self.decoder_chunk_look_back = 1
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = self._initialize()
        self.stream_model = self._initialize_stream()

    def _initialize(self) -> AutoModel:
        logger.info("正在初始化ASR模型...")
        try:
            return AutoModel(
                model="paraformer-zh",
                # vad_model="fsmn-vad",
                # vad_kwargs={"max_single_segment_time": 30000},
                device=self.device,
                disable_update=True,
            )
        except Exception as e:
            logger.error("初始化ASR模型失败: %s", e)
            raise e

    def _initialize_stream(self):
        logger.info("正在初始化ASR流式模型...")
        try:
            return AutoModel(model="paraformer-zh-streaming", disable_update=True)
        except Exception as e:
            logger.error("初始化ASR流式模型失败: %s", e)
            raise e

    def transcribe(self, audio_file: str) -> str:
        logger.info("开始ASR识别...")
        try:
            start_time = time.time()
            res = self.model.generate(
                input=audio_file,
                cache={},
                language="zn",  # "zn", "en", "yue", "ja", "ko", "nospeech"
                use_itn=True,
                batch_size_s=60,
                merge_vad=True,  #
                merge_length_s=15,
            )
            logger.info("ASR识别完成，耗时: %.2f秒", time.time() - start_time)
            return rich_transcription_postprocess(res[0]["text"]).replace(" ", "")
        except Exception as e:
            logger.error("ASR识别失败: %s", e)
            raise

    async def stream_transcribe(self, audio_file):
        logger.info("开始ASR流式识别...")
        try:
            start_time = time.time()
            speech, _ = sf.read(audio_file)
            chunk_stride = self.chunk_size[1] * 960

            cache = {}
            total_chunk_num = int(len((speech) - 1) / chunk_stride + 1)
            for i in range(total_chunk_num):
                speech_chunk = speech[i * chunk_stride : (i + 1) * chunk_stride]
                is_final = i == total_chunk_num - 1
                res = self.stream_model.generate(
                    input=speech_chunk,
                    cache=cache,
                    is_final=is_final,
                    chunk_size=self.chunk_size,
                    encoder_chunk_look_back=self.encoder_chunk_look_back,
                    decoder_chunk_look_back=self.decoder_chunk_look_back,
                )
                yield res[0].get("text")
            logger.info("ASR流式识别完成，耗时: %.2f秒", time.time() - start_time)
        except Exception as e:
            logger.error("ASR流式识别失败: %s", e)
            raise
