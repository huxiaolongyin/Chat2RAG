from haystack import component
from typing import List, Any
from haystack.dataclasses import ChatMessage
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import json
from rag_core.utils.logger import logger
from rag_core.tools.tool_manage import ToolManager

# 默认函数执行超时时间(秒)
DEFAULT_TIMEOUT = 3

tool_manager = ToolManager()


@component
class FunctionExecutor:
    """进行函数调用"""

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.executor = ThreadPoolExecutor()

    def _execute_function(self, function_name: str, **kwargs) -> Any:
        """执行单个函数调用"""
        future = self.executor.submit(
            tool_manager.execute_function, function_name, **kwargs
        )
        try:
            return future.result(timeout=self.timeout)
        except TimeoutError:
            raise TimeoutError(f"函数执行超过{self.timeout}秒")

    @component.output_types(response=List[str])
    def run(
        self,
        function_info: List[ChatMessage],
    ) -> list:
        """
        传入函数信息和函数映射字典，返回函数调用结果

        Args:
            function_info: 函数信息
        Returns:
            dict: 包含函数调用结果的字典
        """
        function_responses = []
        for item in function_info:
            calls = json.loads(item.content)
            for call in calls:
                function_name = call["function"]["name"]
                function_args = json.loads(call["function"]["arguments"])

                # if function_name not in [*functions, *tool_manager.built_in_tools.keys]:
                #     logger.error(f"未找到函数: {function_name}")
                #     continue
                logger.info(f"执行函数调用: {function_name}，参数为{function_args}")
                try:
                    result = self._execute_function(function_name, **function_args)
                    function_responses.append(f"执行{function_name}得到结果{result}")
                except TimeoutError:
                    logger.error(f"函数{function_name}执行超时")
                    function_responses.append(
                        f"调用{function_name}内容, 执行超时, 请稍后重试"
                    )
                except Exception as e:
                    logger.error(f"函数 {function_name} 执行出错: {str(e)}")
                    function_responses.append(
                        f"调用{function_name}失败, 参数为{function_args}， 请稍后重试"
                    )

        return {"response": function_responses}
