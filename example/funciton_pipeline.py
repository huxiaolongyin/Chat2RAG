import asyncio

from chat2rag.pipelines.funciton import FunctionPipeline
from chat2rag.tools import tool_manager

all_tool = tool_manager.fetch_tools(["maps_weather"])
function_pipeline = FunctionPipeline(tools=all_tool)
print(asyncio.run(function_pipeline.run("今天福州天气怎么样")))
