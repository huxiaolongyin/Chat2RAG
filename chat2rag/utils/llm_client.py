from openai import AsyncOpenAI

from chat2rag.config import CONFIG


# OpenAI 客户端初始化
class LLMClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=CONFIG.OPENAI_API_KEY,
            base_url=CONFIG.OPENAI_BASE_URL,
        )

    async def acall_llm(
        self,
        messages: list[dict],
        model: str = "Qwen/Qwen2.5-32B-Instruct",
        max_tokens: int = 20,
        temperature: float = 0.0,
    ) -> str:
        """异步调用 LLM"""
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            extra_body={"enable_thinking": False},
        )
        return response.choices[0].message.content.strip()
