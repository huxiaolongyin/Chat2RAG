import asyncio
import time
from typing import List

from haystack import Pipeline
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.components.tools.tool_invoker import ToolInvoker
from haystack.dataclasses import ChatMessage
from haystack.tools import Tool
from haystack.utils import Secret

from chat2rag.config import CONFIG
from chat2rag.logger import get_logger
from chat2rag.pipelines.base import BasePipeline
from chat2rag.tools.tool_manager import tool_manager

logger = get_logger(__name__)

all_tools = tool_manager.get_tools()


class FunctionPipeline(BasePipeline):
    def __init__(self, intention_model: str = CONFIG.DEFAULT_INTENTION_MODEL):
        self.intention_model = intention_model
        self.pipeline = self._initialize_pipeline()
        super().__init__()

    def _initialize_pipeline(self):
        """
        Initialize Function pipeline
        """
        logger.debug("Initialize function pipeline...")
        try:
            pipeline = Pipeline()
            pipeline.add_component(
                "intention",
                OpenAIChatGenerator(
                    model=self.intention_model,
                    api_key=Secret.from_env_var("OPENAI_API_KEY"),
                    api_base_url=CONFIG.OPENAI_BASE_URL,
                ),
            )
            pipeline.add_component("tool_invoker", ToolInvoker(tools=all_tools))
            pipeline.connect("intention.replies", "tool_invoker.messages")
            logger.debug("Function pipeline initialized successfully")
            return pipeline

        except Exception as e:
            logger.error("Failed to initialize function pipeline: %s", e)
            raise

    def warm_up(self):
        """
        Warm up the function pipeline by loading necessary models and resources
        """
        logger.debug("Warm up the function pipeline...")
        try:
            self.pipeline.warm_up()
            logger.debug("Function pipeline warm up successfully")

        except Exception as e:
            logger.error("Failed to warm up function pipeline: %s", e)
            raise

    async def run(
        self,
        query: str,
        prefix_prompt: str = None,
        history_messages: List[ChatMessage] = [],
        tools: List[Tool] = [],
    ) -> dict:
        """
        Run the function pipeline
        Args:
            query: The user query
            prefix_prompt: The prefix prompt for the prompt template
            history_messages: The history messages for the prompt template
            tools: The tools for the prompt template
        """
        start_time = time.time()
        if not CONFIG.FUNCION_ENABLED:
            logger.debug(
                "Passing function pipeline due to CONFIG.FUNCION_ENABLED is False"
            )
            return {}
        messages = [
            ChatMessage.from_system(prefix_prompt + CONFIG.FUNCTION_PROMPT_TEMPLATE),
            *history_messages,
            ChatMessage.from_user(query),
        ]
        try:
            result = await asyncio.to_thread(
                self.pipeline.run,
                data={
                    "intention": {
                        "messages": messages,
                        "tools": tools,
                    }
                },
            )
            logger.info(
                "Function pipeline run successfully in %.2f seconds",
                time.time() - start_time,
            )
            logger.debug("Function pipeline result: %s", result)
            return result
        except Exception as e:
            logger.error("Failed to run function pipeline: %s", e)
            raise
