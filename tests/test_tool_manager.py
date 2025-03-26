import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import responses
import yaml
from haystack.tools import Tool

from chat2rag.tools.tool_manager import ToolManager


@pytest.fixture
def sample_yaml_content():
    return """
tools:
  - type: api
    function:
      name: test_api
      description: Test API
      url: https://example.com/api
      method: GET
      parameters:
        type: object
        properties:
          query:
            type: string
            description: Search query
"""


@pytest.fixture
def temp_yaml_file(tmp_path, sample_yaml_content):
    """创建一个临时YAML文件并写入测试数据"""
    yaml_path = tmp_path / "test_tools.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(sample_yaml_content)
    yield yaml_path
    # 测试结束后pytest会自动清理tmp_path目录


class TestToolManager:

    @patch("chat2rag.tools.tool_manager.get_logger")
    @patch("chat2rag.tools.tool_manager.Tool")
    @patch("chat2rag.tools.tool_manager.Path")
    def test_init(self, mock_path, mock_tool, mock_logger):
        # Setup mocks
        mock_path.return_value.parent.__truediv__.return_value = "default_path"
        mock_logger.return_value = MagicMock()

        with patch.object(ToolManager, "load_tools") as mock_load:
            # Initialize ToolManager
            manager = ToolManager()

            # Verify initialization
            assert manager.tools == []
            assert manager.custom_tools == []
            assert manager.tool_list == []
            mock_load.assert_called_once()

    @patch("chat2rag.tools.tool_manager.get_logger")
    def test_load_yaml_tools(self, mock_logger, temp_yaml_file):
        """使用真实临时文件测试YAML工具加载"""
        # Setup logger mock
        mock_logger.return_value = MagicMock()

        # 创建一个用于测试的简单API函数
        def simple_api_function(**kwargs):
            return {"result": "success"}

        # 初始化ToolManager，禁用内置工具加载
        with patch.object(ToolManager, "load_builtin_tools"):
            with patch.object(
                ToolManager, "_create_api_function", return_value=simple_api_function
            ):
                # 使用临时YAML文件初始化ToolManager
                manager = ToolManager(tools_yaml_path=temp_yaml_file)

                # 清空可能已经加载的工具
                manager.tools = []
                manager.tool_list = []
                manager.custom_tools = []

                # 调用load_yaml_tools方法
                manager.load_yaml_tools(temp_yaml_file)

                # 验证工具是否正确加载
                assert len(manager.tools) == 1, "应该加载一个工具"
                assert len(manager.custom_tools) == 1, "应该加载一个自定义工具"
                assert len(manager.tool_list) == 1, "工具列表应该有一个项目"

                # 验证工具数据
                tool_data = manager.tool_list[0]
                assert tool_data["type"] == "api"
                assert tool_data["function"]["name"] == "test_api"
                assert tool_data["function"]["url"] == "https://example.com/api"

    @patch("chat2rag.tools.tool_manager.get_logger")
    @responses.activate
    def test_api_function(self, mock_logger):
        # Setup
        mock_logger.return_value = MagicMock()
        manager = ToolManager()

        # 模拟API响应
        responses.add(
            responses.GET,
            "https://example.com/api",
            json={"result": "success"},
            status=200,
        )

        # 创建API函数并测试
        api_function = manager._create_api_function(
            "test_api", "https://example.com/api", "GET"
        )

        result = api_function(param="value")
        assert result == {"result": "success"}

    @patch("chat2rag.tools.tool_manager.get_logger")
    def test_add_custom_tool(self, mock_logger, tmp_path):
        """测试添加自定义工具"""
        # 创建临时YAML文件路径
        yaml_path = tmp_path / "tools.yaml"

        # 设置mocks
        mock_logger.return_value = MagicMock()

        with patch.object(ToolManager, "load_builtin_tools"):
            with patch.object(ToolManager, "_save_yaml_tools"):
                # 初始化ToolManager
                manager = ToolManager(tools_yaml_path=yaml_path)
                manager.tools = []
                manager.custom_tools = []
                manager.tool_list = []

                # 添加自定义工具
                result = manager.add_custom_tool(
                    name="new_api",
                    description="New API",
                    url="https://example.com/new",
                    method="POST",
                    parameters={
                        "type": "object",
                        "properties": {
                            "data": {"type": "string", "description": "Data to send"}
                        },
                    },
                )

                # 验证结果
                assert result is True
                assert len(manager.tools) == 1
                assert len(manager.custom_tools) == 1
                assert len(manager.tool_list) == 1

    @patch("chat2rag.tools.tool_manager.get_logger")
    def test_update_custom_tool(self, mock_logger, tmp_path):
        """测试更新自定义工具"""
        # 创建临时YAML文件路径
        yaml_path = tmp_path / "tools.yaml"

        # 设置mocks
        mock_logger.return_value = MagicMock()

        with patch.object(ToolManager, "load_builtin_tools"):
            with patch.object(ToolManager, "_save_yaml_tools"):
                # 初始化ToolManager
                manager = ToolManager(tools_yaml_path=yaml_path)

                # 创建测试工具
                test_tool = Tool(
                    name="test_api",
                    description="Test API",
                    parameters={"type": "object"},
                    function=lambda: None,
                )
                manager.tools = [test_tool]
                manager.custom_tools = [test_tool]
                manager.tool_list = [
                    {
                        "type": "api",
                        "function": {
                            "name": "test_api",
                            "description": "Test API",
                            "url": "https://example.com/api",
                            "method": "GET",
                            "parameters": {"type": "object"},
                        },
                    }
                ]

                # 测试更新
                result = manager.update_custom_tool(
                    name="test_api",
                    description="Updated API",
                    url="https://example.com/updated",
                    method="POST",
                )

                # 验证结果
                assert result is True
                assert manager.tool_list[0]["function"]["description"] == "Updated API"
                assert (
                    manager.tool_list[0]["function"]["url"]
                    == "https://example.com/updated"
                )
                assert manager.tool_list[0]["function"]["method"] == "POST"

    @patch("chat2rag.tools.tool_manager.get_logger")
    def test_delete_custom_tool(self, mock_logger, tmp_path):
        """测试删除自定义工具"""
        # 创建临时YAML文件路径
        yaml_path = tmp_path / "tools.yaml"

        # 设置mocks
        mock_logger.return_value = MagicMock()

        with patch.object(ToolManager, "load_builtin_tools"):
            with patch.object(ToolManager, "_save_yaml_tools"):
                # 初始化ToolManager
                manager = ToolManager(tools_yaml_path=yaml_path)

                # 创建测试工具
                test_tool = Tool(
                    name="test_api",
                    description="Test API",
                    parameters={"type": "object"},
                    function=lambda: None,
                )
                manager.tools = [test_tool]
                manager.custom_tools = [test_tool]
                manager.tool_list = [
                    {
                        "type": "api",
                        "function": {
                            "name": "test_api",
                            "description": "Test API",
                            "url": "https://example.com/api",
                            "method": "GET",
                            "parameters": {"type": "object"},
                        },
                    }
                ]

                # 测试删除
                result = manager.delete_custom_tool("test_api")

                # 验证结果
                assert result is True
                assert len(manager.tools) == 0
                assert len(manager.custom_tools) == 0
                assert len(manager.tool_list) == 0

    @patch("chat2rag.tools.tool_manager.get_logger")
    def test_get_tool_by_name(self, mock_logger):
        """测试通过名称获取工具"""
        # 设置mocks
        mock_logger.return_value = MagicMock()

        with patch.object(ToolManager, "load_tools"):
            # 初始化ToolManager
            manager = ToolManager()

            # 创建测试工具
            test_tool = Tool(
                name="test_api",
                description="Test API",
                parameters={"type": "object"},
                function=lambda: None,
            )
            manager.tools = [test_tool]

            # 测试获取存在的工具
            tool = manager.get_tool_by_name("test_api")
            assert tool is test_tool

            # 测试获取不存在的工具
            tool = manager.get_tool_by_name("non_existent")
            assert tool is None
