import yaml
import requests
from enum import Enum
from pathlib import Path
from typing import Dict, List, Union
from .weather import get_weather_info, weather_info
from .weibo import get_weibo_info, weibo_info
from .translit import get_translit_info, translit_info
from .today import get_today_info, today_info
from .bazi import get_bazi_info, bazi_info


class ToolType(Enum):
    BUILT_IN = "built_in"
    API = "api"


class ToolManager:
    def __init__(self):
        self.config_path = Path(__file__).parent / "tools.yaml"

        # 内置工具配置
        self.built_in_tools = {
            "weather_tool": {
                "functions": get_weather_info,
                "info": weather_info,
                "type": ToolType.BUILT_IN,
            },
            "weibo_tool": {
                "functions": get_weibo_info,
                "info": weibo_info,
                "type": ToolType.BUILT_IN,
            },
            "translit_tool": {
                "functions": get_translit_info,
                "info": translit_info,
                "type": ToolType.BUILT_IN,
            },
            "today_tool": {
                "functions": get_today_info,
                "info": today_info,
                "type": ToolType.BUILT_IN,
            },
            "bazi_tool": {
                "functions": get_bazi_info,
                "info": bazi_info,
                "type": ToolType.BUILT_IN,
            },
        }
        # 自定义工具
        self.api_tools = self._load_api_tools()

    def _load_api_tools(self) -> List[Dict]:
        """加载自定义工具"""
        if not self.config_path.exists():
            return []
        with open(self.config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config.get("tools", [])

    def _save_tool_info(self):
        """保存工具配置到yaml文件"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump({"tools": self.api_tools}, f, allow_unicode=True)

    def _tool_exists(self, tool_name: str) -> bool:
        """检查工具是否存在"""
        return tool_name in self.built_in_tools or any(
            t["function"]["name"] == tool_name for t in self.api_tools
        )

    def add_api_tool(self, tool_config: Dict) -> bool:
        """添加新工具
        Args:
            tool_config: 工具配置字典,需包含function字段
        Returns:
            True: 添加成功
            False: 添加失败
        """
        if "function" not in tool_config:
            return False

        tool_name = tool_config["function"]["name"]
        if self._tool_exists(tool_name):
            return False

        self.api_tools.append(tool_config)
        self._save_tool_info()
        return True

    def remove_api_tool(self, tool_name: str) -> bool:
        """删除指定工具
        Args:
            tool_name: 工具名称
        returns:
            True: 删除成功
            False: 删除失败
        """
        for i, tool in enumerate(self.api_tools):
            if tool["function"]["name"] == tool_name:
                self.api_tools.pop(i)
                self._save_tool_info()
                return True
        return False

    def get_all_tools(self) -> List[Dict]:
        """获取所有工具信息(包含内置和自定义)"""
        tools = []
        # 添加内置工具
        for tool in self.built_in_tools.values():
            tool_info = tool["info"].copy()
            tool_info["type"] = ToolType.BUILT_IN.value
            tools.append(tool_info)

        # 添加自定义工具
        for tool in self.api_tools:
            tool_info = {
                "type": ToolType.API.value,
                "function": tool["function"],
            }
            tools.append(tool_info)
        return tools

    def get_all_tools_open_ai(self) -> List[Dict]:
        """获取所有工具信息(包含内置和自定义), openai的格式"""
        all_tools = self.get_all_tools()

        return [
            {
                "type": "function",
                "function": {
                    "name": tool["function"]["name"],
                    "description": tool["function"]["description"],
                    "parameters": tool["function"]["parameters"],
                },
                "required": tool.get("required", []),
            }
            for tool in all_tools
        ]

    def get_tool_info(self, tool_names: Union[list, str] = None) -> list:
        """获取工具信息, openai的格式"""
        all_tools = self.get_all_tools_open_ai()
        if not tool_names:
            return []
        if isinstance(tool_names, str) and tool_names.lower() == "all":
            return all_tools
        return [tool for tool in all_tools if tool["function"]["name"] in tool_names]

    def execute_function(self, function_name: str, **kwargs):
        """
        执行函数
        Args:
            function_name: 函数名称
            **kwargs: 函数参数
        Returns:
            函数返回值
        """
        if function_name in self.built_in_tools:
            return self.built_in_tools[function_name]["functions"](**kwargs)
        else:
            for tool in self.api_tools:
                if tool["function"]["name"] == function_name:
                    url = tool["function"]["url"]
                    method = tool["function"]["method"]
                    response = requests.request(method, url, params=kwargs)
                    return response
            return None
