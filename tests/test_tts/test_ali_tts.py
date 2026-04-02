import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chat2rag.providers.tts.cosy_voice_tts import CosyVoiceTTS


class TestCosyVoiceTTS:
    def test_init(self):
        tts = CosyVoiceTTS(voice="longanyang")
        assert tts.voice == "longanyang"
        assert tts.speed == 1.0
        assert tts._connected is False

    def test_init_default_voice(self):
        tts = CosyVoiceTTS()
        assert tts.voice == "longanyang"

    def test_get_available_voices(self):
        tts = CosyVoiceTTS()
        voices = tts.get_available_voices()
        assert len(voices) == 5
        assert any(v["id"] == "longanyang" for v in voices)
        assert any(v["name"] == "龙昂扬" for v in voices)

    def test_should_send_text_with_punctuation(self):
        tts = CosyVoiceTTS()
        tts._text_buffer = "这是第一句话。"
        assert tts._should_send_text() is True

    def test_should_send_text_without_punctuation(self):
        tts = CosyVoiceTTS()
        tts._text_buffer = "这是一段没有标点的文本"
        assert tts._should_send_text() is False

    def test_should_send_text_long_enough(self):
        tts = CosyVoiceTTS()
        tts._text_buffer = "a" * 60
        assert tts._should_send_text() is True

    def test_extract_sentence_with_punctuation(self):
        tts = CosyVoiceTTS()
        tts._text_buffer = "这是第一句话。这是第二句话"
        sentence = tts._extract_sentence()
        assert sentence == "这是第一句话。"
        assert tts._text_buffer == "这是第二句话"

    def test_extract_sentence_long_text(self):
        tts = CosyVoiceTTS()
        tts._text_buffer = "a" * 60
        sentence = tts._extract_sentence()
        assert len(sentence) == 60
        assert tts._text_buffer == ""

    def test_extract_sentence_short_text(self):
        tts = CosyVoiceTTS()
        tts._text_buffer = "短文本"
        sentence = tts._extract_sentence()
        assert sentence == ""
        assert tts._text_buffer == "短文本"

    @pytest.mark.asyncio
    async def test_speak_raises_error(self):
        tts = CosyVoiceTTS()
        with pytest.raises(NotImplementedError):
            tts.speak("test")

    @pytest.mark.asyncio
    async def test_stream_speak_raises_error(self):
        tts = CosyVoiceTTS()
        with pytest.raises(NotImplementedError):
            async for _ in tts.stream_speak("test"):
                pass

    @pytest.mark.asyncio
    async def test_append_text_when_not_connected(self):
        tts = CosyVoiceTTS()
        tts._connected = False
        tts._text_buffer = ""

        await tts.append_text("test")
        assert tts._text_buffer == ""

    @pytest.mark.asyncio
    async def test_get_audio_nowait_empty_queue(self):
        tts = CosyVoiceTTS()
        tts._audio_queue = None
        result = await tts.get_audio_nowait()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_audio_nowait_with_data(self):
        tts = CosyVoiceTTS()
        tts._audio_queue = asyncio.Queue()
        test_data = b"test audio"
        await tts._audio_queue.put(test_data)

        result = await tts.get_audio_nowait()
        assert result == test_data

    @pytest.mark.asyncio
    async def test_speak_sentence_empty_text(self):
        tts = CosyVoiceTTS()
        result = await tts.speak_sentence("")
        assert result is None

    @pytest.mark.asyncio
    async def test_speak_sentence_whitespace_only(self):
        tts = CosyVoiceTTS()
        result = await tts.speak_sentence("   ")
        assert result is None

    @pytest.mark.asyncio
    async def test_warmup_creates_synthesizer(self):
        tts = CosyVoiceTTS()
        assert tts._sentence_synthesizer is None

        await tts.warmup()
        assert tts._sentence_synthesizer is not None
        assert tts._sentence_queue is not None
        assert tts._sentence_lock is not None

    @pytest.mark.asyncio
    async def test_warmup_idempotent(self):
        tts = CosyVoiceTTS()
        await tts.warmup()
        first_synthesizer = tts._sentence_synthesizer

        await tts.warmup()
        assert tts._sentence_synthesizer == first_synthesizer

    @pytest.mark.asyncio
    async def test_speak_sentence_uses_warmed_synthesizer(self):
        tts = CosyVoiceTTS()
        await tts.warmup()
        initial_synthesizer = tts._sentence_synthesizer

        with patch.object(tts._sentence_synthesizer, "call") as mock_call:
            with patch.object(tts._sentence_queue, "get") as mock_get:
                mock_call.return_value = None
                mock_get.side_effect = [None]

                await tts.speak_sentence("测试文本", timeout=1.0)

                mock_call.assert_called_once_with("测试文本")

    @pytest.mark.asyncio
    async def test_close_clears_sentence_synthesizer(self):
        tts = CosyVoiceTTS()
        await tts.warmup()

        tts._connected = True
        tts._synthesizer = MagicMock()
        tts._complete_event = MagicMock()
        tts._complete_event.wait = MagicMock()

        await tts.close()

        assert tts._sentence_synthesizer is None
        assert tts._sentence_queue is None
        assert tts._sentence_callback is None


class TestCosyVoiceTTSIntegration:
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        "DASHSCOPE_API_KEY" not in __import__("os").environ,
        reason="DASHSCOPE_API_KEY not set",
    )
    async def test_speak_sentence_real(self):
        tts = CosyVoiceTTS(voice="longanyang")
        audio = await tts.speak_sentence("你好世界", timeout=10.0)

        assert audio is not None
        assert isinstance(audio, bytes)
        assert audio[:4] == b"RIFF"
        assert audio[8:12] == b"WAVE"

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        "DASHSCOPE_API_KEY" not in __import__("os").environ,
        reason="DASHSCOPE_API_KEY not set",
    )
    async def test_connect_append_close_real(self):
        tts = CosyVoiceTTS(voice="longanyang")

        await tts.connect()
        assert tts._connected is True

        await tts.append_text("这是第一句话。")
        await tts.append_text("这是第二句话。")
        await tts.finish_text()

        audio_chunks = []
        async for audio in tts.get_audio():
            if audio:
                audio_chunks.append(audio)

        await tts.close()
        assert tts._connected is False

        if audio_chunks:
            for chunk in audio_chunks:
                assert chunk[:4] == b"RIFF"
