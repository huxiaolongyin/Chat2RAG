import json
import os
import uuid
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from chat2rag.api.service.audio_processor import AudioProcessor
from chat2rag.core.tts.kokorotts import KokoroTTS
from chat2rag.logger import get_logger

# Setup logging
logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Chat2RAG API", description="Voice-enabled chat interface for RAG systems"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, specify actual origins
    # TODO: 🔴P1 安全问题：生产环境中应限制具体的origins，而不是使用通配符"*"，以防止跨站请求伪造攻击
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure temp directories exist
os.makedirs("tmp/voice", exist_ok=True)
# TODO: 🟡P3 临时文件管理：添加定期清理临时音频文件的机制，避免磁盘空间浪费
# TODO: 🟡P2 配置管理：将临时目录路径提取为配置变量，以便更容易地进行更改和管理

# Initialize audio processor
audio_processor = AudioProcessor()
# TODO: 🟡P2 依赖注入：应该在应用启动时初始化AudioProcessor，并通过依赖注入使用，而不是全局实例


@app.get("/")
async def web():
    """Serve the web interface"""
    return FileResponse("chat2rag/api/static/index.html")
    # TODO: 🟡P2 路径管理：使用相对路径可能导致问题，建议使用绝对路径或配置变量


@app.get("/voice_list")
async def voice_list():
    """Get the list of available voices"""
    voices = KokoroTTS.get_available_voices()
    return {"voices": voices}


@app.websocket("/ws/chat/audio")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for audio chat"""
    await websocket.accept()
    logger.info("WebSocket connection established")

    # Add connection to active set
    audio_processor.active_connections.add(websocket)

    # Reset state for new connection
    speech_segments = []
    vad_active = False
    selected_voice = None
    # TODO: 🟡P2 状态管理：考虑将连接状态封装到一个类中，以便更好地管理每个连接的状态

    try:
        while True:
            # 接收消息 - 可能是配置JSON或音频数据
            message = await websocket.receive()
            # logger.debug(f"Received message: {message}")
            # TODO: 🟠P2 超时处理：添加接收超时机制，防止连接空闲过长时间

            # 判断消息类型
            if "text" in message:  # JSON消息
                try:
                    config = json.loads(message["text"])
                    if "type" in config and config["type"] == "config":
                        # 处理配置消息
                        if "voice" in config:
                            selected_voice = config["voice"]
                            # 更新TTS的语音选择
                            audio_processor.tts.set_voice(selected_voice)
                            logger.info(f"Voice changed to: {selected_voice}")
                            # 确认配置已应用
                            await audio_processor.safe_send_json(
                                websocket,
                                {"type": "config_applied", "voice": selected_voice},
                            )
                except json.JSONDecodeError:
                    logger.warning("Received invalid JSON message")
                continue

            elif "bytes" in message:  # 二进制音频数据
                audio_bytes = message["bytes"]
                # logger.debug(f"Received {len(audio_bytes)} bytes of audio data")

                # 处理音频数据...
                # Process through VAD
                vad_result = audio_processor.process_audio_chunk(audio_bytes)
                if not vad_result:
                    continue

                # Extract VAD status
                vad_status = vad_result.get("vad_status")

                # If VAD is already active, collect speech segments
                if vad_active:
                    speech_segments.append(vad_result.get("voice"))

                # Skip if no VAD status
                if vad_status is None:
                    continue

                # Handle VAD start
                if "start" in vad_status:
                    vad_active = True
                    speech_segments.append(vad_result.get("voice"))
                    # TODO: 🟡P3 重复代码：这里和前面的speech_segments.append重复，可以优化逻辑

                # Handle VAD end - this means we have a complete speech segment to process
                elif "end" in vad_status and len(speech_segments) > 0:
                    logger.debug(
                        f"Received speech segment with {len(speech_segments)} chunks"
                    )
                    vad_active = False

                    # Generate a unique filename for this audio segment
                    timestamp = datetime.now().date()
                    unique_id = uuid.uuid4().hex
                    audio_file = os.path.join(
                        "tmp/voice", f"asr-{timestamp}@{unique_id}.wav"
                    )
                    # TODO: 🟡P2 文件管理：应该实现一个自动清理机制，避免长时间运行后临时文件堆积

                    # Save audio for ASR processing
                    if audio_processor.save_audio_to_file(speech_segments, audio_file):
                        # Transcribe audio to text
                        text = audio_processor.transcribe_audio(audio_file)
                        # TODO: 🟠P2 错误处理：应添加对transcribe_audio可能失败的错误处理

                        if text.strip():
                            # Send transcription to client
                            json_sent = await audio_processor.safe_send_json(
                                websocket,
                                {"type": "text", "role": "user", "text": text},
                            )

                            if json_sent:
                                logger.info(f"ASR result: {text}")

                                # Generate and stream LLM response
                                full_response = (
                                    await audio_processor.generate_llm_response(
                                        text, websocket, selected_voice
                                    )
                                )
                                # TODO: 🔴P1 错误处理：LLM响应生成失败时应有合适的错误处理机制

                                # Send completion signal
                                await audio_processor.safe_send_json(
                                    websocket, {"type": "done", "text": full_response}
                                )
                            else:
                                logger.warning(
                                    "Failed to send ASR result, connection may be closed"
                                )
                        else:
                            logger.warning("ASR produced empty transcription")
                            await audio_processor.safe_send_json(
                                websocket,
                                {
                                    "type": "warning",
                                    "message": "Couldn't understand audio. Please try again.",
                                },
                            )
                            # TODO: 🟡P3 用户体验：应该提供更具体的错误信息，帮助用户解决问题

                    # Reset speech segments for next utterance
                    speech_segments = []

    except WebSocketDisconnect:
        logger.info("WebSocket connection closed by client")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        # TODO: 🔴P1 错误处理：应该记录更详细的错误信息，包括堆栈跟踪，以便调试

        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except:
            pass
            # TODO: 🟠P2 异常捕获：不应使用空的except语句，应指定具体异常类型并记录日志
    finally:
        # Remove connection from active set
        audio_processor.active_connections.discard(websocket)
        logger.info("WebSocket connection removed from active connections")
        # TODO: 🟡P2 资源清理：应确保所有为此连接分配的资源都被正确释放


if __name__ == "__main__":
    import uvicorn

    # Use multiple workers for better performance in production
    uvicorn.run(app, host="0.0.0.0", port=8000)
    # TODO: 🟡P2 配置管理：主机和端口应从配置文件或环境变量中读取，而不是硬编码
