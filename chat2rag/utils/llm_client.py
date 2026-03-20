from openai import AsyncOpenAI

from chat2rag.config import CONFIG
from chat2rag.models.models import ModelProvider, ModelSource
from chat2rag.services.model_service import model_source_service


class LLMClient:
    _clients: dict[str, AsyncOpenAI] = {}

    def _get_client(self, base_url: str, api_key: str) -> AsyncOpenAI:
        key = f"{base_url}|{api_key}"
        if key not in self._clients:
            self._clients[key] = AsyncOpenAI(api_key=api_key, base_url=base_url)
        return self._clients[key]

    async def acall_llm(
        self,
        messages: list[dict],
        model: str = CONFIG.PROCESS_MODEL,
        max_tokens: int = 20,
        temperature: float = 0.0,
        extra_log: str = "LLM",
    ) -> str:
        model_source: ModelSource = await model_source_service.get_best_source(
            model, extra_log=extra_log
        )
        model_provider: ModelProvider = await model_source.provider
        client = self._get_client(model_provider.base_url, model_provider.api_key)
        response = await client.chat.completions.create(
            model=model_source.name,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            extra_body={"enable_thinking": False},
        )
        return response.choices[0].message.content.strip()
