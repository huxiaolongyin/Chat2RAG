import asyncio
import base64
from io import StringIO
from typing import AsyncGenerator, AsyncIterator

from chat2rag.core.logger import get_logger
from chat2rag.providers.tts import BaseTTS
from chat2rag.schemas.chat import Audio, AudioContent
from chat2rag.streaming.constants import (
    AUDIO_QUEUE_MAX_SIZE,
    BEHAVIOR_TAG_PATTERN,
    TTS_BATCH_TIMEOUT,
    TTS_MAX_BATCH_SIZE,
    TTS_PUNCTUATION_MARKS,
    TEXT_QUEUE_MAX_SIZE,
)

logger = get_logger(__name__)


class TTSProcessor:
    def __init__(self, tts_provider: BaseTTS, audio_config: Audio):
        self.tts_provider = tts_provider
        self.audio_config = audio_config

        self._audio_queue: asyncio.Queue = asyncio.Queue(maxsize=AUDIO_QUEUE_MAX_SIZE)
        self._text_queue: asyncio.Queue = asyncio.Queue(maxsize=TEXT_QUEUE_MAX_SIZE)

        self._worker_task: asyncio.Task | None = None
        self._running = False
        self._initialized = False

        self._text_buffer = StringIO()
        self._initialized_lock = asyncio.Lock()

    async def initialize(self) -> bool:
        async with self._initialized_lock:
            if self._initialized:
                return True

            try:
                if hasattr(self.tts_provider, "warm_up"):
                    await self.tts_provider.warm_up()

                self._initialized = True
                logger.info(f"TTS processor initialized: {self.tts_provider}")
                return True

            except Exception:
                logger.exception("Failed to initialize TTS provider")
                return False

    async def start_worker(self):
        if not self._initialized:
            success = await self.initialize()
            if not success:
                logger.error("TTS processor initialization failed, worker not started")
                return

        self._running = True
        self._worker_task = asyncio.create_task(self._tts_worker_loop())
        logger.debug("TTS worker started")

    async def stop_worker(self):
        if self._worker_task:
            try:
                await self._text_queue.put(None)
                await asyncio.wait_for(self._worker_task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("TTS worker timeout, cancelling")
                self._worker_task.cancel()
                try:
                    await self._worker_task
                except asyncio.CancelledError:
                    pass
            except asyncio.CancelledError:
                pass

            self._worker_task = None

        self._running = False
        self._text_buffer = StringIO()
        logger.debug("TTS worker stopped")

    async def add_text(self, text: str):
        if not self._running or not text:
            return

        try:
            self._text_queue.put_nowait(text)
        except asyncio.QueueFull:
            logger.warning("TTS text queue full, dropping text chunk")

    async def get_audio(self, timeout: float = 0.1) -> tuple[str, str, dict] | None:
        try:
            audio_data = await asyncio.wait_for(
                self._audio_queue.get(), timeout=timeout
            )
            return audio_data
        except asyncio.TimeoutError:
            return None
        except asyncio.QueueEmpty:
            return None

    async def drain_audio_queue(
        self, timeout: float = 5.0
    ) -> AsyncIterator[tuple[str, str, dict]]:
        while True:
            try:
                audio_data = await asyncio.wait_for(
                    self._audio_queue.get(), timeout=timeout
                )
                if audio_data is None:
                    break
                yield audio_data
            except asyncio.TimeoutError:
                break

    async def _tts_worker_loop(self):
        buffer = StringIO()

        try:
            while self._running:
                texts = []

                try:
                    first_text = await asyncio.wait_for(
                        self._text_queue.get(), timeout=0.1
                    )
                    if first_text is None:
                        break
                    texts.append(first_text)
                except asyncio.TimeoutError:
                    continue

                for _ in range(TTS_MAX_BATCH_SIZE - 1):
                    try:
                        text = self._text_queue.get_nowait()
                        if text is None:
                            break
                        texts.append(text)
                    except asyncio.QueueEmpty:
                        break

                combined_text = "".join(texts)
                buffer.write(combined_text)

                clean_text = BEHAVIOR_TAG_PATTERN.sub("", buffer.getvalue())

                last_punct_pos = max(
                    (clean_text.rfind(mark) for mark in TTS_PUNCTUATION_MARKS),
                    default=-1,
                )

                if last_punct_pos >= 0:
                    sentence = clean_text[: last_punct_pos + 1]
                    remaining = clean_text[last_punct_pos + 1 :]

                    buffer = StringIO()
                    buffer.write(remaining)

                    await self._process_sentence(sentence)

            if buffer.getvalue().strip():
                final_text = buffer.getvalue().strip()
                await self._process_sentence(final_text)

        except asyncio.CancelledError:
            if buffer.getvalue().strip():
                try:
                    await self._process_sentence(buffer.getvalue().strip())
                except Exception:
                    pass
        except Exception:
            logger.exception("TTS worker error")

    async def _process_sentence(self, sentence: str):
        if not sentence or not sentence.strip():
            return

        try:
            if hasattr(self.tts_provider, "speak_sentence"):
                audio_bytes = await self.tts_provider.speak_sentence(sentence)
            else:
                audio_bytes = await self.tts_provider.speak(sentence)

            if audio_bytes:
                audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
                audio_data = ("audio", sentence, audio_base64, None)

                try:
                    self._audio_queue.put_nowait(audio_data)
                except asyncio.QueueFull:
                    logger.warning("Audio queue full, dropping audio chunk")

        except Exception:
            logger.warning(f"TTS process error for sentence: {sentence[:50]}")

    def build_audio_content(self, text: str, audio_base64: str) -> AudioContent:
        return AudioContent(
            text=text,
            audio_base64=audio_base64,
            format=self.audio_config.format,
            sample_rate=self.audio_config.sample_rate,
        )

    async def close(self):
        await self.stop_worker()

        if hasattr(self.tts_provider, "close"):
            try:
                await self.tts_provider.close()
            except Exception:
                logger.exception("Error closing TTS provider")

        logger.info("TTS processor closed")

    def is_running(self) -> bool:
        return self._running

    def get_queue_sizes(self) -> dict:
        return {
            "text_queue": self._text_queue.qsize(),
            "audio_queue": self._audio_queue.qsize(),
        }
