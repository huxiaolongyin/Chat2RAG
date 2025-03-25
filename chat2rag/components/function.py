import json
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any, List

from haystack import component
from haystack.dataclasses import ChatMessage

from chat2rag.logger import get_logger
from chat2rag.tools.tool_manage import ToolManager

logger = get_logger(__name__)
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
        logger.debug(
            "Starting function : <%s>; call_kwargs: <%s>", function_name, kwargs
        )
        start_time = time.time()
        future = self.executor.submit(
            tool_manager.execute_function, function_name, **kwargs
        )
        try:
            result = future.result(timeout=self.timeout)
            logger.debug(
                "Function <%s> execution completed in %.2f seconds",
                function_name,
                time.time() - start_time,
            )
            return result
        except TimeoutError:
            logger.error("Function execution timed out after %s seconds", self.timeout)
            raise TimeoutError(f"函数执行超过{self.timeout}秒")
        except Exception as e:
            logger.error("Function <%s> execution failed: %s", function_name, e)
            raise e

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

        try:
            function_responses = []
            for item in function_info:
                calls = json.loads(item.text)
                for call in calls:
                    function_name = call["function"]["name"]
                    function_args = json.loads(call["function"]["arguments"])

                    try:
                        result = self._execute_function(function_name, **function_args)
                        function_responses.append(
                            f"执行{function_name}得到结果{result}"
                        )
                    except TimeoutError:
                        function_responses.append(
                            f"调用{function_name}内容, 执行超时, 请稍后重试"
                        )
                    except Exception as e:
                        function_responses.append(
                            f"调用{function_name}失败, 参数为{function_args}， 请稍后重试"
                        )
        except Exception as e:
            function_responses = ""
            raise Exception(f"调用函数失败, 参数为{function_info}, 请稍后重试")

        return {"response": function_responses}
