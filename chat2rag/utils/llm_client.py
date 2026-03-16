from openai import AsyncOpenAI

from chat2rag.config import CONFIG
from chat2rag.models.models import ModelProvider, ModelSource
from chat2rag.services.model_service import ModelSourceService

model_source_service = ModelSourceService()


# OpenAI 客户端初始化
class LLMClient:
    async def acall_llm(
        self,
        messages: list[dict],
        model: str = CONFIG.PROCESS_MODEL,
        max_tokens: int = 20,
        temperature: float = 0.0,
        extra_log: str = "LLM",
    ) -> str:
        """异步调用 LLM"""

        model_source: ModelSource = await model_source_service.get_best_source(
            model, extra_log=extra_log
        )
        model_provider: ModelProvider = await model_source.provider
        self.client = AsyncOpenAI(
            api_key=model_provider.api_key,
            base_url=model_provider.base_url,
        )
        response = await self.client.chat.completions.create(
            model=model_source.name,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            extra_body={"enable_thinking": False},
        )
        return response.choices[0].message.content.strip()
