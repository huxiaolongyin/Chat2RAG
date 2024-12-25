import os
from typing import Dict, List
import requests
import yaml


class ToolManager:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.tools_yaml_path = os.path.join(current_dir, "tools.yaml")
        functions = self._load_functions()
        self.tools = functions.get("tools", [])

    def _load_functions(self) -> Dict:
        with open(self.tools_yaml_path, "r", encoding="utf-8") as f:
            functions = yaml.safe_load(f)
        return functions

    def _save_functions(self):
        """保存工具配置到yaml文件"""
        with open(self.tools_yaml_path, "w", encoding="utf-8") as f:
            yaml.safe_dump({"tools": self.tools}, f, allow_unicode=True)

    def add_tool(self, tool_config: Dict) -> bool:
        """添加新工具
        Args:
            tool_config: 工具配置字典,需包含function字段
        Returns:
            bool: 添加是否成功
        """
        if "function" not in tool_config:
            return False

        tool_name = tool_config["function"]["name"]
        # 检查是否已存在同名工具
        if tool_name in self.get_tools_name():
            return False

        self.tools.append(tool_config)
        self._save_functions()
        return True

    def remove_tool(self, tool_name: str) -> bool:
        """删除指定工具
        Args:
            tool_name: 工具名称
        Returns:
            bool: 删除是否成功
        """
        for i, tool in enumerate(self.tools):
            if tool["function"]["name"] == tool_name:
                self.tools.pop(i)
                self._save_functions()
                return True
        return False

    def get_tools_name(self) -> List[str]:
        """获取工具名称列表"""
        return [tool["function"]["name"] for tool in self.tools]

    def get_model_functions(self) -> List[Dict]:
        """获取OpenAI格式的函数定义"""

        return [
            {
                "type": "function",
                "function": {
                    "name": tool["function"]["name"],
                    "description": tool["function"]["description"],
                    "parameters": tool["function"]["parameters"],
                },
            }
            for tool in self.tools
        ]

    def execute_function(self, function_name: str, **params):
        """执行函数调用"""
        url = ""
        for tool in self.tools:
            if tool["function"]["name"] == function_name:
                url = tool["function"]["url"]
                method = tool["function"].get("method", "GET")
        if url:
            response = requests.request(method, url, json=params)
            return response.json()
