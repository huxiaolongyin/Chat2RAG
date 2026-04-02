import base64
import json
import re

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from chat2rag.providers.tts import CosyVoiceTTS
from chat2rag.schemas.base import BaseResponse
from chat2rag.schemas.chat import Audio
from chat2rag.schemas.voice import TTSRequest, TTSResponse, VoiceInfo

router = APIRouter()

PUNCTUATION_PATTERN = re.compile(r"[，。！？；：、,\.!?;:\n]+")


def split_text_to_sentences(text: str, max_length: int = 100) -> list[str]:
    sentences = PUNCTUATION_PATTERN.split(text)
    sentences = [s.strip() for s in sentences if s.strip()]

    result = []
    for sentence in sentences:
        while len(sentence) > max_length:
            result.append(sentence[:max_length])
            sentence = sentence[max_length:]
        if sentence:
            result.append(sentence)

    return result if result else [text]


@router.get("/list", summary="获取可用语音列表")
async def get_voices():
    tts = CosyVoiceTTS(Audio())
    voices = tts.get_available_voices()
    return BaseResponse.success(data=[VoiceInfo(**v) for v in voices])


@router.post("/tts", summary="文本转语音")
async def text_to_speech(request: TTSRequest):
    audio_config = Audio(
        voice=request.voice,
        speed=request.speed,
        format=request.format,
        sample_rate=request.sample_rate,
    )
    tts = CosyVoiceTTS(audio_config)
    await tts.warm_up()

    if request.return_type == "stream":

        async def audio_stream():
            audio_bytes = await tts.speak_sentence(request.text)
            if audio_bytes:
                yield audio_bytes

        return StreamingResponse(
            audio_stream(),
            media_type=f"audio/{request.format}",
            headers={"Content-Disposition": f"attachment; filename=tts_{request.voice}.{request.format}"},
        )

    audio_bytes = await tts.speak_sentence(request.text)
    if not audio_bytes:
        return BaseResponse.error(msg="TTS生成失败", code="5000")

    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
    return BaseResponse.success(
        data=TTSResponse(
            audio=audio_base64,
            format=request.format,
            sample_rate=request.sample_rate,
        ),
        msg="TTS生成成功",
    )


@router.post("/tts/stream", summary="流式文本转语音")
async def text_to_speech_stream(request: TTSRequest):
    audio_config = Audio(
        voice=request.voice,
        speed=request.speed,
        format=request.format,
        sample_rate=request.sample_rate,
    )
    tts = CosyVoiceTTS(audio_config)
    await tts.warm_up()

    sentences = split_text_to_sentences(request.text)

    async def sse_generator():
        chunk_index = 0
        for sentence in sentences:
            try:
                audio_bytes = await tts.speak_sentence(sentence)
                if audio_bytes:
                    data = json.dumps(
                        {
                            "audio": base64.b64encode(audio_bytes).decode("utf-8"),
                            "index": chunk_index,
                        }
                    )
                    yield f"data: {data}\n\n"
                    chunk_index += 1
            except Exception as e:
                error_data = json.dumps({"error": str(e)})
                yield f"data: {error_data}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
