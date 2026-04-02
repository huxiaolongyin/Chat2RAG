import asyncio
import os
import threading
from typing import AsyncGenerator

import dashscope
from dashscope.audio.tts_v2 import AudioFormat, ResultCallback, SpeechSynthesizer

from chat2rag.core.logger import get_logger
from chat2rag.providers.tts.base import BaseTTS
from chat2rag.schemas.chat import Audio

logger = get_logger(__name__)


class SentenceTTSCallback(ResultCallback):
    def __init__(self, audio_queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        self.audio_queue = audio_queue
        self.loop = loop
        self._wav_buffer: list[bytes] = []

    def on_open(self) -> None:
        logger.debug("CosyVoice connection opened")

    def on_close(self) -> None:
        logger.debug("CosyVoice connection closed")

    def on_data(self, data: bytes) -> None:
        self._wav_buffer.append(data)
        logger.debug(f"Received audio chunk: {len(data)} bytes")

    def on_complete(self) -> None:
        if self._wav_buffer:
            combined_wav = b"".join(self._wav_buffer)
            asyncio.run_coroutine_threadsafe(
                self.audio_queue.put(combined_wav), self.loop
            )
            self._wav_buffer.clear()
        asyncio.run_coroutine_threadsafe(self.audio_queue.put(None), self.loop)

    def on_error(self, message: str) -> None:
        logger.error(f"CosyVoice error: {message}")
        asyncio.run_coroutine_threadsafe(self.audio_queue.put(None), self.loop)

    def on_event(self, message):
        logger.debug(f"CosyVoice event: {message}")


class StreamSentenceCallback(ResultCallback):
    def __init__(self, audio_queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        self.audio_queue = audio_queue
        self.loop = loop

    def on_open(self) -> None:
        logger.debug("StreamSentence connection opened")

    def on_close(self) -> None:
        logger.debug("StreamSentence connection closed")
        asyncio.run_coroutine_threadsafe(self.audio_queue.put(None), self.loop)

    def on_data(self, data: bytes) -> None:
        asyncio.run_coroutine_threadsafe(self.audio_queue.put(data), self.loop)
        logger.debug(f"StreamSentence received chunk: {len(data)} bytes")

    def on_complete(self) -> None:
        logger.debug("StreamSentence response done")
        asyncio.run_coroutine_threadsafe(self.audio_queue.put(None), self.loop)

    def on_error(self, message: str) -> None:
        logger.error(f"StreamSentence error: {message}")
        asyncio.run_coroutine_threadsafe(self.audio_queue.put(None), self.loop)

    def on_event(self, message):
        logger.debug(f"StreamSentence event: {message}")


PUNCTUATION_MARKS = [
    ",",
    ".",
    "，",
    "。",
    "!",
    "?",
    "！",
    "？",
    ";",
    "；",
    ":",
    "：",
    "、",
]


class CosyVoiceCallback(ResultCallback):
    def __init__(
        self,
        audio_queue: asyncio.Queue,
        loop: asyncio.AbstractEventLoop,
        complete_event: threading.Event,
    ):
        self.audio_queue = audio_queue
        self.loop = loop
        self.complete_event = complete_event
        self._wav_buffer: list[bytes] = []
        self.first_audio_received = False

    def on_open(self) -> None:
        logger.debug("CosyVoice connection opened")

    def on_close(self) -> None:
        logger.debug("CosyVoice connection closed")
        self.complete_event.set()

    def on_data(self, data: bytes) -> None:
        if not self.first_audio_received:
            self.first_audio_received = True
            logger.info("CosyVoice first audio received")

        self._wav_buffer.append(data)
        logger.debug(f"Received {len(data)} bytes audio data")

    def on_complete(self) -> None:
        logger.debug("CosyVoice response done")
        if self._wav_buffer:
            combined_wav = b"".join(self._wav_buffer)
            asyncio.run_coroutine_threadsafe(
                self.audio_queue.put(combined_wav), self.loop
            )
            self._wav_buffer.clear()

    def on_error(self, message: str) -> None:
        logger.error(f"CosyVoice error: {message}")

    def on_event(self, message):
        logger.debug(f"CosyVoice event: {message}")


class CosyVoiceTTS(BaseTTS):
    def __init__(self, audio_config: Audio):
        self._audio_queue: asyncio.Queue | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._complete_event: threading.Event | None = None
        self._synthesizer: SpeechSynthesizer | None = None
        self._callback: CosyVoiceCallback | None = None
        self._connected = False
        self._text_buffer = ""
        self._finished_text = False

        self._sentence_queue: asyncio.Queue | None = None
        self._sentence_loop: asyncio.AbstractEventLoop | None = None
        self._sentence_callback: SentenceTTSCallback | None = None
        self._sentence_synthesizer: SpeechSynthesizer | None = None
        self._sentence_lock: asyncio.Lock | None = None

        self._init_dashscope_api_key()
        super().__init__(audio_config)

    def _init_dashscope_api_key(self):
        if "DASHSCOPE_API_KEY" in os.environ:
            dashscope.api_key = os.environ["DASHSCOPE_API_KEY"]
        else:
            logger.warning("DASHSCOPE_API_KEY not found in environment variables")

        dashscope.base_websocket_api_url = (
            "wss://dashscope.aliyuncs.com/api-ws/v1/inference"
        )

    def _initialize(self):
        pass

    def _get_audio_format(self) -> AudioFormat:
        format_name = self.format.lower()
        sample_rate = self.sample_rate

        format_mapping = {
            "wav": {
                8000: AudioFormat.WAV_8000HZ_MONO_16BIT,
                16000: AudioFormat.WAV_16000HZ_MONO_16BIT,
                22050: AudioFormat.WAV_22050HZ_MONO_16BIT,
                24000: AudioFormat.WAV_24000HZ_MONO_16BIT,
                44100: AudioFormat.WAV_44100HZ_MONO_16BIT,
                48000: AudioFormat.WAV_48000HZ_MONO_16BIT,
            },
            "pcm": {
                8000: AudioFormat.PCM_8000HZ_MONO_16BIT,
                16000: AudioFormat.PCM_16000HZ_MONO_16BIT,
                22050: AudioFormat.PCM_22050HZ_MONO_16BIT,
                24000: AudioFormat.PCM_24000HZ_MONO_16BIT,
                44100: AudioFormat.PCM_44100HZ_MONO_16BIT,
                48000: AudioFormat.PCM_48000HZ_MONO_16BIT,
            },
            "mp3": {
                8000: AudioFormat.MP3_8000HZ_MONO_128KBPS,
                16000: AudioFormat.MP3_16000HZ_MONO_128KBPS,
                22050: AudioFormat.MP3_22050HZ_MONO_256KBPS,
                24000: AudioFormat.MP3_24000HZ_MONO_256KBPS,
                44100: AudioFormat.MP3_44100HZ_MONO_256KBPS,
                48000: AudioFormat.MP3_48000HZ_MONO_256KBPS,
            },
            "ogg_opus": {
                8000: AudioFormat.OGG_OPUS_8KHZ_MONO_32KBPS,
                16000: AudioFormat.OGG_OPUS_16KHZ_MONO_32KBPS,
                24000: AudioFormat.OGG_OPUS_24KHZ_MONO_32KBPS,
                48000: AudioFormat.OGG_OPUS_48KHZ_MONO_32KBPS,
            },
        }

        if format_name in format_mapping:
            if sample_rate in format_mapping[format_name]:
                return format_mapping[format_name][sample_rate]

        logger.warning(
            f"Unsupported format={format_name} or sample_rate={sample_rate}, falling back to WAV_24000HZ_MONO_16BIT"
        )
        return AudioFormat.WAV_24000HZ_MONO_16BIT

    async def warm_up(self) -> None:
        if self._sentence_synthesizer is not None:
            return

        self._sentence_queue = asyncio.Queue()
        self._sentence_loop = asyncio.get_running_loop()
        self._sentence_lock = asyncio.Lock()
        self._sentence_callback = SentenceTTSCallback(
            audio_queue=self._sentence_queue,
            loop=self._sentence_loop,
        )

        self._sentence_synthesizer = SpeechSynthesizer(
            model="cosyvoice-v3-flash",
            voice=self.voice,
            format=self._get_audio_format(),
            callback=self._sentence_callback,
            speech_rate=self.speed,
        )
        logger.info(
            f"CosyVoice sentence synthesizer warmed up with voice={self.voice}, format={self.format}, sample_rate={self.sample_rate}"
        )

    async def _rebuild_sentence_synthesizer(self) -> None:
        self._sentence_queue = asyncio.Queue()
        self._sentence_callback = SentenceTTSCallback(
            audio_queue=self._sentence_queue,
            loop=self._sentence_loop,
        )

        self._sentence_synthesizer = SpeechSynthesizer(
            model="cosyvoice-v3-flash",
            voice=self.voice,
            format=self._get_audio_format(),
            callback=self._sentence_callback,
            speech_rate=self.speed,
        )
        logger.debug("CosyVoice sentence synthesizer rebuilt")

    async def connect(self):
        self._audio_queue = asyncio.Queue()
        self._loop = asyncio.get_running_loop()
        self._complete_event = threading.Event()

        self._callback = CosyVoiceCallback(
            audio_queue=self._audio_queue,
            loop=self._loop,
            complete_event=self._complete_event,
        )

        self._synthesizer = SpeechSynthesizer(
            model="cosyvoice-v3-flash",
            voice=self.voice,
            format=self._get_audio_format(),
            callback=self._callback,
        )

        self._connected = True
        self._finished_text = False
        self._text_buffer = ""
        logger.info(
            f"CosyVoice connected with voice={self.voice}, format={self.format}, sample_rate={self.sample_rate}"
        )

    async def append_text(self, text: str):
        if not self._connected or not self._synthesizer:
            logger.warning("CosyVoice not connected, cannot append text")
            return

        self._text_buffer += text

        if self._should_send_text():
            sentence = self._extract_sentence()
            if sentence:
                logger.debug(f"CosyVoice streaming_call: {sentence}")
                self._synthesizer.streaming_call(sentence)

    def _should_send_text(self) -> bool:
        for punct in PUNCTUATION_MARKS:
            if punct in self._text_buffer:
                return True
        return len(self._text_buffer) >= 50

    def _extract_sentence(self) -> str:
        last_punct_pos = max(
            (self._text_buffer.rfind(mark) for mark in PUNCTUATION_MARKS),
            default=-1,
        )

        if last_punct_pos >= 0:
            sentence = self._text_buffer[: last_punct_pos + 1]
            self._text_buffer = self._text_buffer[last_punct_pos + 1 :]
            return sentence

        if len(self._text_buffer) >= 50:
            sentence = self._text_buffer
            self._text_buffer = ""
            return sentence

        return ""

    async def finish_text(self):
        if not self._connected or not self._synthesizer:
            return

        if self._finished_text:
            return

        if self._text_buffer:
            logger.debug(
                f"CosyVoice finishing with remaining text: {self._text_buffer}"
            )
            self._synthesizer.streaming_call(self._text_buffer)
            self._text_buffer = ""

        self._synthesizer.streaming_complete()
        self._finished_text = True
        logger.info("CosyVoice text input finished")

    async def get_audio(self) -> AsyncGenerator[bytes | None, None]:
        if not self._audio_queue:
            return

        while True:
            try:
                audio = await asyncio.wait_for(self._audio_queue.get(), timeout=0.5)
                yield audio
                if audio is None:
                    break
            except asyncio.TimeoutError:
                if self._finished_text and self._complete_event.is_set():
                    break
                continue

    async def get_audio_nowait(self) -> bytes | None:
        if not self._audio_queue:
            return None

        try:
            return self._audio_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    async def close(self):
        if not self._connected:
            return

        if not self._finished_text:
            await self.finish_text()

        self._complete_event.wait(timeout=5)

        self._connected = False
        self._synthesizer = None
        self._callback = None

        self._sentence_synthesizer = None
        self._sentence_callback = None
        self._sentence_queue = None

        logger.info("CosyVoice connection closed")

    def speak(self, text: str, voice: str = None) -> tuple[bytes, int]:
        raise NotImplementedError(
            "CosyVoice uses async streaming, use connect/append_text/get_audio instead"
        )

    async def stream_speak(
        self, text: str, voice: str = None
    ) -> AsyncGenerator[tuple[bytes, int], None]:
        raise NotImplementedError(
            "CosyVoice uses connect/append_text/get_audio instead"
        )

    async def speak_sentence(self, text: str, timeout: float = 10.0) -> bytes | None:
        if not text or not text.strip():
            return None

        async with self._sentence_lock:
            if self._sentence_synthesizer is None:
                await self.warm_up()

            try:
                self._sentence_synthesizer.call(text)

                audio_chunks = []
                while True:
                    try:
                        audio = await asyncio.wait_for(
                            self._sentence_queue.get(), timeout=timeout
                        )
                        if audio is None:
                            break
                        audio_chunks.append(audio)
                    except asyncio.TimeoutError:
                        logger.warning(
                            f"speak_sentence timeout after {timeout}s for text: {text[:50]}..."
                        )
                        break

                self._sentence_synthesizer = None
                self._sentence_queue = asyncio.Queue()
                asyncio.create_task(self._rebuild_sentence_synthesizer())

                if audio_chunks:
                    return b"".join(audio_chunks)
                return None

            except Exception as e:
                logger.exception(f"speak_sentence error: {e}")
                self._sentence_synthesizer = None
                asyncio.create_task(self._rebuild_sentence_synthesizer())
                return None

    async def speak_sentence_stream(
        self, text: str, timeout: float = 30.0
    ) -> AsyncGenerator[bytes, None]:
        if not text or not text.strip():
            return

        stream_queue: asyncio.Queue = asyncio.Queue()
        stream_loop = asyncio.get_running_loop()
        stream_callback = StreamSentenceCallback(
            audio_queue=stream_queue, loop=stream_loop
        )

        synthesizer = SpeechSynthesizer(
            model="cosyvoice-v3-flash",
            voice=self.voice,
            format=self._get_audio_format(),
            callback=stream_callback,
            speech_rate=self.speed,
        )

        try:
            synthesizer.call(text)

            while True:
                try:
                    audio = await asyncio.wait_for(stream_queue.get(), timeout=timeout)
                    if audio is None:
                        break
                    yield audio
                except asyncio.TimeoutError:
                    logger.warning(
                        f"speak_sentence_stream timeout after {timeout}s for text: {text[:50]}..."
                    )
                    break

        except Exception as e:
            logger.exception(f"speak_sentence_stream error: {e}")

    def get_available_voices(self) -> list[dict]:
        return [
            {
                "id": "longanhuan",
                "name": "龙安欢",
                "language": "zh",
                "gender": "female",
            },
            {"id": "longanyang", "name": "龙安洋", "language": "zh", "gender": "male"},
            {
                "id": "longhuhu_v3",
                "name": "龙呼呼",
                "language": "zh",
                "gender": "child",
            },
            {
                "id": "longpaopao_v3",
                "name": "龙泡泡",
                "language": "zh",
                "gender": "child",
            },
            {
                "id": "longjielidou_v3",
                "name": "龙杰力豆",
                "language": "zh",
                "gender": "child",
            },
        ]
