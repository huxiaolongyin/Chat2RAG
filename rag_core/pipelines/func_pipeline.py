from haystack import Pipeline
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.components.routers import ConditionalRouter
from haystack.dataclasses import ChatMessage
from typing import List
from rag_core.config import CONFIG
from rag_core.components import FunctionExecutor


class FunctionPipeline:
    """函数调用管道"""

    def __init__(
        self,
        intention_model: str,
    ):
        self.intention_model = intention_model
        self._initialize_pipeline()
        self.warm_up()

    def __str__(self):
        return str(self.pipeline)

    def __repr__(self):
        return str(self.pipeline)

    def _initialize_pipeline(self):
        """初始化函数调用管道"""
        intention = OpenAIChatGenerator(
            model=self.intention_model,
            api_key=CONFIG.OPENAI_API_KEY,
            api_base_url=CONFIG.OPENAI_BASE_URL,
        )
        routes = [
            {
                "condition": "{{ 'function' in replies[0].text or 'arguments' in replies[0].text }}",
                "output": "{{replies}}",
                "output_name": "function_calls",
                "output_type": List[ChatMessage],
            },
            {
                "condition": "{{ 'function' not in replies[0].text }}",
                "output": "No need to call a function",
                "output_name": "no_function_calls",
                "output_type": str,
            },
        ]
        self.pipeline = Pipeline()
        self.pipeline.add_component("intention", intention)
        self.pipeline.add_component(
            "router", ConditionalRouter(routes, unsafe=True, validate_output_type=True)
        )
        self.pipeline.add_component("function_executor", FunctionExecutor())
        self.pipeline.connect("intention.replies", "router")
        self.pipeline.connect("router.function_calls", "function_executor")

    def warm_up(self):
        """预热"""
        self.pipeline.warm_up()

    async def run(
        self,
        query: str,
        tools: list,
        functions: dict,
        messages: List[ChatMessage] = None,
    ):
        """运行函数调用管道"""
        messages = [
            ChatMessage.from_system(
                "你是专门来意图识别的助手，你的任务是识别用户意图，并根据意图返回相应的工具。如果没有获取到函数或工具，请返回None。"
            ),
            *messages,
            ChatMessage.from_user(query),
        ]
        return self.pipeline.run(
            data={
                "intention": {
                    "messages": messages,
                    "generation_kwargs": {"tools": tools},
                },
                "function_executor": {"functions": functions},
            }
        )


async def main():
    from rag_core.tools import weather_info, get_current_weather

    pipeline = FunctionPipeline()
    tools = [weather_info]
    functions = {
        "weather_tool": get_current_weather,
    }
    response = await pipeline.run(
        query="北京天气怎么样", tools=tools, functions=functions
    )
    print(response)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
