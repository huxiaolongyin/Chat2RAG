import asyncio
from time import perf_counter
from typing import AsyncIterator

from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.dataclasses import ChatMessage, ImageContent, StreamingChunk
from haystack.utils import Secret

from chat2rag.config import CONFIG
from chat2rag.core.logger import get_logger

from .base import ResponseStrategy

logger = get_logger(__name__)


class MultiModalStrategy(ResponseStrategy):
    """多模态处理策略"""

    async def can_handle(self, query: str) -> bool:
        return self.request.content.image

    async def execute(self, query: str) -> AsyncIterator[str]:
        # history_messages = await chat_history.get_history_messages(
        #     self.request.prompt_name,
        #     self.request.chat_id,
        #     self.request.chat_rounds,
        #     image=self.request.content.get("image", ""),
        # )
        task = asyncio.create_task(self._process_pipeline())
        try:
            async for chunk in self.handler.get_stream(self.is_batch):
                yield chunk
        finally:
            await task

    async def _process_pipeline(self):
        try:
            image_data = self.request.content.image
            multiModal = OpenAIChatGenerator(
                model=CONFIG.MULTIMODAL_MODEL,
                api_base_url=CONFIG.MULTIMODAL_API_URL,
                api_key=Secret.from_token(CONFIG.MULTIMODAL_API_KEY),
                streaming_callback=self.handler.callback,
                generation_kwargs={
                    "extra_body": {"stream_options": {"include_usage": True}}
                },
            )
            if image_data.startswith(("http://", "https://")):
                image = ImageContent.from_url(image_data, detail="low")
            else:
                if image_data.startswith("data:image"):
                    image_data = image_data.split(",", 1)[1]
                image = ImageContent(base64_image=image_data, detail="low")

            user_message = ChatMessage.from_user(content_parts=[self.query, image])
            result = await multiModal.run_async([user_message])
            message = result.get("replies")[0]
            usage = message.meta.get("usage", {})

            # 记录 token 使用
            if usage:
                input_tokens = int(usage.get("prompt_tokens", 0))
                output_tokens = int(usage.get("completion_tokens", 0))
                self.handler.set_token_info(input_tokens, output_tokens)

            logger.info(
                f"MultiModal processed: answer='{message.text}', cost={perf_counter() - self.start_time:.2f}s"
            )

        except Exception as e:
            logger.exception("Failed to execute multimodal strategy")
            self.handler.set_error(str(e))
            await self.handler.callback(
                StreamingChunk(
                    content="交互发生了一点小问题，等待工程师爸爸修复",
                    meta={"model": "error", "finish_reason": "error"},
                )
            )
        finally:
            logger.debug("Sending END signal to stream")
            await self.handler.finish()
            logger.debug("END signal sent")
