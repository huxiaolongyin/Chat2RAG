import asyncio
from time import perf_counter
from typing import List

from haystack import Pipeline
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.components.routers import ConditionalRouter
from haystack.dataclasses import ChatMessage

from rag_core.components import FunctionExecutor
from rag_core.config import CONFIG
from rag_core.logging import logger


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
        """
        Initialize Function pipeline
        """
        logger.info("Initialize function pipeline...")

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

        logger.info("Function pipeline initialize successfully")

    def warm_up(self):
        """
        Warm up the function pipeline
        """
        logger.info("Warm up the function pipeline")
        self.pipeline.warm_up()
        logger.info("Function pipeline warm up successfully")

    async def run(
        self,
        query: str,
        tools: list,
        messages: List[ChatMessage] = None,
        template: str = CONFIG.FUNCTION_PROMPT_TEMPLATE,
    ):
        """
        Running the function pipeline.
        """
        logger.info(f"Running function pipeline with query: <{query}>...")
        start = perf_counter()
        messages = [
            ChatMessage.from_system(template),
            *messages,
            ChatMessage.from_user(query),
        ]
        # result = ""
        result = await asyncio.to_thread(
            self.pipeline.run,
            data={
                "intention": {
                    "messages": messages,
                    "generation_kwargs": {"tools": tools},
                }
            },
        )
        logger.info(
            f"Function pipeline ran successfully. Cost: {perf_counter() - start:.3f} s; Result: {result};"
        )

        return result
