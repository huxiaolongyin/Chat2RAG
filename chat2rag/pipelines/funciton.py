import asyncio
import time
from typing import List

from haystack import Pipeline
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.components.tools.tool_invoker import ToolInvoker
from haystack.dataclasses import ChatMessage
from haystack.tools import Toolset
from haystack.utils import Secret
from haystack_integrations.tools.mcp import MCPToolset

from chat2rag.config import CONFIG
from chat2rag.logger import get_logger
from chat2rag.pipelines.base import BasePipeline

logger = get_logger(__name__)


class FunctionPipeline(BasePipeline):
    def __init__(
        self,
        tools: Toolset | MCPToolset,
        intention_model: str = CONFIG.DEFAULT_INTENTION_MODEL,
    ):
        self.intention_model = intention_model
        self.tools = tools
        super().__init__()

    def _initialize_pipeline(self):
        """
        Initialize the Function pipeline
        """

        logger.debug("Initializing the Function pipeline...")
        try:
            pipeline = Pipeline()
            pipeline.add_component(
                "intention",
                OpenAIChatGenerator(
                    model=self.intention_model,
                    api_key=Secret.from_env_var("OPENAI_API_KEY"),
                    api_base_url=CONFIG.OPENAI_BASE_URL,
                    tools=self.tools,
                ),
            )
            pipeline.add_component("tool_invoker", ToolInvoker(self.tools))
            pipeline.connect("intention.replies", "tool_invoker.messages")
            logger.debug("Function pipeline initialized successfully.")
            return pipeline

        except Exception as e:
            logger.error(
                "Failed to initialize the Function pipeline. Failure reason: %s", e
            )
            raise

    async def run(
        self,
        query: str,
        prefix_prompt: str = "",
        history_messages: List[ChatMessage] = [],
    ) -> dict:
        """
        Run the Function pipeline

        Args:
            query: User query
            prefix_prompt: Prompt template's prefix prompt
            history_messages: Prompt template's chat history
        """
        start_time = time.time()
        if not CONFIG.FUNCION_ENABLED:
            logger.debug(
                "Since FUNCION_ENABLED is configured to False, the Function pipeline is skipped"
            )
            return {}

        messages = [
            ChatMessage.from_system(prefix_prompt + CONFIG.FUNCTION_PROMPT_TEMPLATE),
            *history_messages,
            ChatMessage.from_user(query),
        ]
        try:
            result = await asyncio.to_thread(
                self.pipeline.run, data={"intention": {"messages": messages}}
            )
            logger.info(
                "Function pipeline runtime: %.2f seconds", time.time() - start_time
            )
            logger.debug("Function pipeline result: %s", result)
            return result

        except Exception as e:
            logger.error(
                "Failed to run the Function pipeline. Reasons for failure: %s", e
            )
            raise


if __name__ == "__main__":
    # from haystack_integrations.tools.mcp import SSEServerInfo

    # server_info = SSEServerInfo(
    #     url="https://mcp.amap.com/sse?key=2502b472c2922df3c36c201bfc711018"
    # )
    # htw_server_info = SSEServerInfo(url="http://127.0.0.1:8333/sse")
    # tool_a = MCPToolset(server_info=htw_server_info)
    # tool_b = MCPToolset(server_info=server_info)
    # all_tool = tool_a + tool_b

    from chat2rag.tools.tool_manager import tool_manager

    all_tool = tool_manager.fetch_tools(["mcp-gaode", "mcp-htw"])
    # print(all_tool)
    # print(tool_a + tool_b)
    function_pipeline = FunctionPipeline(tools=all_tool)
    print(asyncio.run(function_pipeline.run("今天福州天气怎么样")))
    # print(
    #     asyncio.run(
    #         function_pipeline.run(
    #             "带我去卫生间",
    #             prefix_prompt="设备码：HTYW993906A994684",
    #         )
    #     )
    # )
