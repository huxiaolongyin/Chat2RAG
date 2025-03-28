import os
import queue

# import threading
import wave
from typing import Any, Dict, List, Optional

from fastapi import WebSocket
from openai import OpenAI
from starlette.websockets import WebSocketState

from chat2rag.core.asr.fun import FunASR
from chat2rag.core.tts.kokorotts import KokoroTTS
from chat2rag.core.vad.silero import SileroVAD
from chat2rag.logger import get_logger

logger = get_logger(__name__)

# Maximum retries for sending messages
MAX_SEND_RETRIES = 3

# Define punctuation marks for TTS segmentation
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


class AudioProcessor:
    """Handles audio processing, VAD, ASR and TTS"""

    def __init__(self):
        # Initialize queues
        self.audio_queue = queue.Queue()
        self.vad_queue = queue.Queue()

        # Initialize speech recognition components
        self.vad = SileroVAD()
        self.asr = FunASR()
        self.tts = KokoroTTS()

        # Initialize LLM client
        self.client = OpenAI(
            base_url="http://121.37.31.80:3001/v1",
            api_key="sk-g7TTvvOTlZlBG6iC51FaB8B3Ac48470c8270935958F1A1Cf",
        )

        # State tracking
        self.speech_segments = []
        self.vad_active = False
        self.active_connections = set()

    def process_audio_chunk(self, audio_bytes: bytes) -> Optional[Dict[str, Any]]:
        """Process a single audio chunk through VAD"""
        try:
            self.audio_queue.put(audio_bytes)
            vad_status = self.vad.is_vad(audio_bytes)

            return {"voice": audio_bytes, "vad_status": vad_status}
        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")
            return None

    def save_audio_to_file(self, audio_data: List[bytes], file_path: str) -> bool:
        """Save audio data to WAV file"""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with wave.open(file_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(b"".join(audio_data))

            logger.info(f"ASR recognition audio saved to: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving audio file: {e}")
            return False

    def transcribe_audio(self, audio_file: str) -> str:
        """Transcribe audio file to text using ASR"""
        try:
            return self.asr.transcribe(audio_file)
        except Exception as e:
            logger.error(f"ASR transcription error: {e}")
            return ""

    async def generate_llm_response(
        self, prompt: str, websocket: WebSocket, voice: str = None
    ) -> str:
        """Generate response from LLM and stream TTS audio"""
        try:
            response = self.client.chat.completions.create(
                model="Qwen2.5-32B",
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )

            full_response = await self.process_and_stream_response(
                response, websocket, voice
            )
            return full_response
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            await self.safe_send_json(websocket, {"type": "error", "message": str(e)})
            return ""

    async def is_websocket_connected(self, websocket: WebSocket) -> bool:
        """Check if websocket is still connected"""
        try:
            # Check connection state if available
            if hasattr(websocket, "client_state"):
                return websocket.client_state == WebSocketState.CONNECTED

            # Alternative check based on application state
            return websocket in self.active_connections
        except Exception:
            return False

    async def safe_send_json(self, websocket: WebSocket, data: dict) -> bool:
        """Safely send JSON data with retry mechanism"""
        if not await self.is_websocket_connected(websocket):
            logger.warning("Cannot send JSON: WebSocket is closed")
            return False

        for attempt in range(MAX_SEND_RETRIES):
            try:
                await websocket.send_json(data)
                return True
            except RuntimeError as e:
                if "close message has been sent" in str(e):
                    logger.warning(
                        f"WebSocket already closed (attempt {attempt+1}/{MAX_SEND_RETRIES})"
                    )
                    return False
                elif attempt < MAX_SEND_RETRIES - 1:
                    logger.warning(
                        f"Error sending JSON data (attempt {attempt+1}/{MAX_SEND_RETRIES}): {e}"
                    )
                else:
                    logger.error(
                        f"Failed to send JSON after {MAX_SEND_RETRIES} attempts: {e}"
                    )
                    return False
            except Exception as e:
                if attempt < MAX_SEND_RETRIES - 1:
                    logger.warning(
                        f"Error sending JSON data (attempt {attempt+1}/{MAX_SEND_RETRIES}): {e}"
                    )
                else:
                    logger.error(
                        f"Failed to send JSON after {MAX_SEND_RETRIES} attempts: {e}"
                    )
                    return False
        return False

    async def safe_send_bytes(self, websocket: WebSocket, data: bytes) -> bool:
        """Safely send binary data with retry mechanism"""
        if not await self.is_websocket_connected(websocket):
            logger.warning("Cannot send bytes: WebSocket is closed")
            return False

        for attempt in range(MAX_SEND_RETRIES):
            try:
                await websocket.send_bytes(data)
                return True
            except RuntimeError as e:
                if "close message has been sent" in str(e):
                    logger.warning(
                        f"WebSocket already closed (attempt {attempt+1}/{MAX_SEND_RETRIES})"
                    )
                    return False
                elif attempt < MAX_SEND_RETRIES - 1:
                    logger.warning(
                        f"Error sending binary data (attempt {attempt+1}/{MAX_SEND_RETRIES}): {e}"
                    )
                else:
                    logger.error(
                        f"Failed to send binary data after {MAX_SEND_RETRIES} attempts: {e}"
                    )
                    return False
            except Exception as e:
                if attempt < MAX_SEND_RETRIES - 1:
                    logger.warning(
                        f"Error sending binary data (attempt {attempt+1}/{MAX_SEND_RETRIES}): {e}"
                    )
                else:
                    logger.error(
                        f"Failed to send binary data after {MAX_SEND_RETRIES} attempts: {e}"
                    )
                    return False
        return False

    async def process_and_stream_response(
        self, response, websocket: WebSocket, voice: str
    ) -> str:
        """Process streaming LLM response and generate TTS at appropriate segments"""
        segment = ""
        full_text = ""

        for chunk in response:
            # First check if connection is still active
            if not await self.is_websocket_connected(websocket):
                logger.warning("WebSocket connection closed during response processing")
                break

            if (
                not chunk
                or not hasattr(chunk.choices[0].delta, "content")
                or not chunk.choices[0].delta.content
            ):
                continue

            content = chunk.choices[0].delta.content.replace("\n", "").replace("\t", "")
            full_text += content
            segment += content

            # Check for punctuation to segment the response
            last_punct_pos = max(
                (segment.rfind(mark) for mark in PUNCTUATION_MARKS), default=-1
            )

            # If we found a punctuation mark, process this segment
            if last_punct_pos >= 0:
                # Extract the segment up to and including the punctuation
                process_part = segment[: last_punct_pos + 1]
                keep_part = segment[last_punct_pos + 1 :]

                try:
                    # Generate audio for this segment
                    audio_data = self.tts.speak(process_part, voice)

                    # Extract audio bytes
                    if isinstance(audio_data, tuple) and len(audio_data) == 2:
                        audio_bytes, _ = audio_data
                    else:
                        audio_bytes = audio_data

                    # Send both text and audio to client using safe send methods
                    if audio_bytes:
                        json_sent = await self.safe_send_json(
                            websocket,
                            {
                                "type": "audio",
                                "role": "assistant",
                                "audio": True,
                                "text": process_part,
                            },
                        )

                        # Only send audio if JSON was sent successfully
                        if json_sent:
                            bytes_sent = await self.safe_send_bytes(
                                websocket, audio_bytes
                            )

                            # If either message failed to send, connection might be closed
                            if not bytes_sent:
                                logger.warning(
                                    "Failed to send audio bytes, aborting processing"
                                )
                                return full_text
                        else:
                            logger.warning(
                                "Failed to send JSON data, aborting processing"
                            )
                            return full_text

                    # Keep the remainder for next segment
                    segment = keep_part

                except Exception as e:
                    logger.error(f"TTS processing error: {e}")
                    logger.exception(e)
                    # Continue processing even if one segment fails

        # Process any remaining text after the stream ends
        if segment.strip() and await self.is_websocket_connected(websocket):
            try:
                logger.debug(f"Processing final TTS segment: {segment}")
                audio_data = self.tts.speak(segment, voice)

                if isinstance(audio_data, tuple) and len(audio_data) == 2:
                    audio_bytes, _ = audio_data
                else:
                    audio_bytes = audio_data

                if audio_bytes:
                    json_sent = await self.safe_send_json(
                        websocket,
                        {
                            "type": "audio",
                            "role": "assistant",
                            "audio": True,
                            "text": segment,
                        },
                    )

                    if json_sent:
                        await self.safe_send_bytes(websocket, audio_bytes)
            except Exception as e:
                logger.error(f"Error processing final TTS segment: {e}")
                logger.exception(e)

        return full_text
