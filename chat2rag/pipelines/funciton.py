import time
from typing import List

from haystack import Pipeline
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.components.tools.tool_invoker import ToolInvoker
from haystack.dataclasses import ChatMessage
from haystack.utils import Secret

from chat2rag.config import CONFIG
from chat2rag.logger import get_logger
from chat2rag.pipelines.base import BasePipeline
from chat2rag.tools import tools

logger = get_logger(__name__)

# 监控
# from chat2rag.telemetry import setup_telemetry

# setup_telemetry()


class FunctionPipeline(BasePipeline):
    def __init__(self, intention_model: str = CONFIG.DEFAULT_INTENTION_MODEL):
        self.intention_model = intention_model
        self.pipeline = self._initialize_pipeline()
        super().__init__()

    def _initialize_pipeline(self) -> Pipeline:
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
            pipeline.add_component("tool_invoker", ToolInvoker(tools=tools))
            pipeline.connect("intention.replies", "tool_invoker.messages")
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

    def run(self, query: str, history_messages: List[ChatMessage] = []) -> dict:
        """
        Run the function pipeline
        """
        logger.info("Running function pipeline with query: <%s>...", query)
        start_time = time.time()
        messages = [
            ChatMessage.from_system(CONFIG.FUNCTION_PROMPT_TEMPLATE),
            *history_messages,
            ChatMessage.from_user(query),
        ]
        try:
            result = self.pipeline.run(
                data={
                    "intention": {
                        "messages": messages,
                        "tools": tools,
                    }
                }
            )
            logger.info(
                "Function pipeline run successfully in %.2f seconds",
                time.time() - start_time,
            )
            return result
        except Exception as e:
            logger.error("Failed to run function pipeline: %s", e)
            raise
