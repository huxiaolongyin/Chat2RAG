import copy
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import requests
import yaml
from haystack.tools import Tool

from chat2rag.logger import get_logger

logger = get_logger(__name__)


class ToolManager:
    """Tool manager responsible for loading and managing built-in and custom tools"""

    def __init__(self, tools_yaml_path=None):
        """
        Initialize the tool manager

        Args:
            tools_yaml_path: Custom tool configuration file path, defaults to tools.yaml in the current file directory
        """
        # Initialize logger

        self.tools: List[Tool] = []
        self.custom_tools: List[Tool] = []  # Store custom tools separately
        self.tool_list: List[Dict[str, Any]] = (
            []
        )  # Store tool list in the specified format

        # Use current file location to load YAML file
        if tools_yaml_path is None:
            self.tools_yaml_path = Path(__file__).parent / "tools.yaml"
        else:
            self.tools_yaml_path = Path(tools_yaml_path)

        # Import built-in tools
        try:
            from .htw_mcp import lead_way_tool
            from .translit import get_translit_info
            from .weather import get_weather_info
            from .weibo import get_weibo_info

            # Define built-in tools list
            self.builtin_tools = [
                get_translit_info,
                get_weather_info,
                get_weibo_info,
                lead_way_tool,
            ]
        except ImportError as e:
            logger.error("Error importing built-in tools, %s", str(e))
            self.builtin_tools = []

        # Load tools immediately on instantiation
        self.load_tools()

    def _process_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process parameters, remove cases where default is null

        Args:
            parameters: Parameter dictionary

        Returns:
            Processed parameter dictionary
        """
        if not parameters:
            return parameters

        # Create a deep copy to prevent modifying the original object
        processed = copy.deepcopy(parameters)
        # Process properties dictionary
        if "properties" in processed and isinstance(processed["properties"], dict):
            for prop_name, prop_value in processed["properties"].items():
                if isinstance(prop_value, dict):
                    # If default is null, remove the default key
                    if "default" in prop_value and prop_value["default"] is None:
                        del prop_value["default"]

                    # Recursively process potentially nested objects
                    if "properties" in prop_value:
                        prop_value = self._process_parameters(prop_value)
        if "required" in processed and isinstance(processed["required"], list):
            processed["required"] = [
                req for req in processed["required"] if req is not None
            ]
        else:
            processed["required"] = []

        return processed

    def load_tools(self) -> None:
        """Load all tools"""
        # Clear existing tools
        logger.info("Loading tools...")
        self.tools = []
        self.tool_list = []

        # Load built-in tools
        self.load_builtin_tools()

        # Load custom tools
        if self.tools_yaml_path.exists():
            self.load_yaml_tools(self.tools_yaml_path)

        logger.info("Finished loading tools, total: %d", len(self.tools))

    def load_builtin_tools(self) -> None:
        """Load built-in tools"""
        # Use built-in tools list
        for tool in self.builtin_tools:
            if isinstance(tool, Tool):
                self.tools.append(tool)

                # Get tool data
                tool_data = tool.to_dict().get("data", {})

                # Process parameters
                processed_parameters = self._process_parameters(
                    tool_data.get("parameters", {})
                )

                # Create tool description in the specified format
                tool_desc = {
                    "type": "built_in",
                    "function": {
                        "name": tool_data.get("name", ""),
                        "description": tool_data.get("description", ""),
                        "parameters": processed_parameters,
                        # "required": tool_data.get("required", []),
                    },
                }

                # Add to tool list
                self.tool_list.append(tool_desc)
                logger.debug("Loaded built-in tool: %s", tool_data.get("name", ""))

    def load_yaml_tools(self, yaml_path: Path) -> None:
        """
        Load tools from YAML file

        Args:
            yaml_path: YAML file path
        """
        try:
            with yaml_path.open("r", encoding="utf-8") as file:
                config = yaml.safe_load(file)

            if not config:
                config = {"tools": []}

            if "tools" not in config:
                config["tools"] = []

            # Clear custom tools list
            self.custom_tools = []

            for tool_config in config["tools"]:
                if tool_config.get("type") == "api":
                    # Process API type tools
                    function_config = tool_config.get("function", {})
                    name = function_config.get("name")
                    description = function_config.get("description", "")
                    url = function_config.get("url", "")
                    method = function_config.get("method", "GET")
                    parameters = function_config.get("parameters", {})

                    if not name or not url:
                        logger.warning(
                            "Incomplete API tool configuration, skipping, funciton: %s",
                            function_config,
                        )
                        continue

                    # Process parameters
                    processed_parameters = self._process_parameters(parameters)

                    # Create API call function
                    api_function = self._create_api_function(name, url, method)

                    # Create Tool instance
                    tool = Tool(
                        name=name,
                        description=description,
                        parameters=processed_parameters,
                        function=api_function,
                    )

                    self.tools.append(tool)
                    self.custom_tools.append(tool)

                    # Add to tool list in the specified format
                    self.tool_list.append(
                        {
                            "type": "api",
                            "function": {
                                "name": name,
                                "description": description,
                                "url": url,
                                "method": method,
                                "parameters": processed_parameters,
                            },
                        }
                    )
                    logger.debug("Loaded custom API tool, name: %s", name)

        except Exception as e:
            logger.error("Error loading YAML tools, Error info: %s", str(e))

    def _save_yaml_tools(self) -> None:
        """Save custom tools to YAML file"""
        try:
            # Build YAML configuration
            tool_configs = []

            for tool in self.custom_tools:
                # Find matching tool description
                for tool_desc in self.tool_list:
                    if (
                        tool_desc.get("type") == "api"
                        and tool_desc.get("function", {}).get("name") == tool.name
                    ):

                        tool_configs.append(tool_desc)
                        break

            # Build complete configuration
            config = {"tools": tool_configs}

            # Save to file
            with self.tools_yaml_path.open("w", encoding="utf-8") as file:
                yaml.safe_dump(
                    config, file, default_flow_style=False, allow_unicode=True
                )

            logger.info(
                "Saved custom tools to file, path: %s, count: %d",
                self.tools_yaml_path,
                len(tool_configs),
            )

        except Exception as e:
            logger.error("Error saving tool configuration, Error info: %s", str(e))

    def _create_api_function(self, name: str, url: str, method: str) -> Callable:
        """
        Create a function that calls an API

        Args:
            name: Function name
            url: API URL
            method: HTTP method (GET or POST)

        Returns:
            API calling function
        """

        def api_function(**kwargs):
            try:
                if method.upper() == "GET":
                    response = requests.get(url, params=kwargs)
                elif method.upper() == "POST":
                    response = requests.post(url, json=kwargs)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error("API call failed, name: %s, Error info: %s", name, str(e))
                return {"error": str(e)}

        # Set function name
        api_function.__name__ = name

        return api_function

    # CRUD methods for custom tools
    def add_custom_tool(
        self,
        name: str,
        description: str,
        url: str,
        method: str,
        parameters: Dict[str, Any],
    ) -> bool:
        """
        Add a custom tool

        Args:
            name: Tool name
            description: Tool description
            url: API URL
            method: HTTP method (GET or POST)
            parameters: Parameter definitions

        Returns:
            Whether the addition was successful
        """
        # Check if tool name already exists
        if self.get_tool_by_name(name) is not None:
            logger.warning("Tool name: <%s> already exists", name)
            return False

        # Process parameters
        processed_parameters = self._process_parameters(parameters)

        # Create API call function
        api_function = self._create_api_function(name, url, method)

        # Create Tool instance
        tool = Tool(
            name=name,
            description=description,
            parameters=processed_parameters,
            function=api_function,
        )

        # Add to tool lists
        self.tools.append(tool)
        self.custom_tools.append(tool)

        # Add to formatted tool list
        tool_desc = {
            "type": "api",
            "function": {
                "name": name,
                "description": description,
                "url": url,
                "method": method,
                "parameters": processed_parameters,
            },
        }
        self.tool_list.append(tool_desc)

        # Save configuration
        self._save_yaml_tools()
        logger.info("Added custom tool, name: %s", name)

        return True

    def update_custom_tool(
        self,
        name: str,
        description: str = None,
        url: str = None,
        method: str = None,
        parameters: Dict[str, Any] = None,
    ) -> bool:
        """
        Update a custom tool

        Args:
            name: Tool name
            description: Tool description
            url: API URL
            method: HTTP method (GET or POST)
            parameters: Parameter definitions

        Returns:
            Whether the update was successful
        """
        # Find tool
        for i, tool in enumerate(self.custom_tools):
            if tool.name == name:
                # Get existing configuration
                existing_desc = None
                for desc in self.tool_list:
                    if (
                        desc.get("type") == "api"
                        and desc.get("function", {}).get("name") == name
                    ):
                        existing_desc = desc
                        break

                if existing_desc is None:
                    return False

                # Update configuration
                function_config = existing_desc["function"]

                if description is not None:
                    function_config["description"] = description

                if url is not None:
                    function_config["url"] = url

                if method is not None:
                    function_config["method"] = method

                if parameters is not None:
                    # Process parameters
                    function_config["parameters"] = self._process_parameters(parameters)

                # Recreate Tool instance
                api_function = self._create_api_function(
                    name, function_config["url"], function_config["method"]
                )

                updated_tool = Tool(
                    name=name,
                    description=function_config["description"],
                    parameters=function_config["parameters"],
                    function=api_function,
                )

                # Update tool lists
                self.custom_tools[i] = updated_tool

                # Find and update main tool list
                for j, t in enumerate(self.tools):
                    if t.name == name:
                        self.tools[j] = updated_tool
                        break

                # Save configuration
                self._save_yaml_tools()
                logger.info("Updated custom tool, name: %s", name)

                return True

        logger.warning("Cannot find custom tool with name: %s", name)
        return False

    def delete_custom_tool(self, name: str) -> bool:
        """
        Delete a custom tool

        Args:
            name: Tool name

        Returns:
            Whether the deletion was successful
        """
        # Find and delete custom tool
        tool_found = False

        # Remove from custom tool list
        self.custom_tools = [t for t in self.custom_tools if t.name != name]

        # Remove from main tool list
        self.tools = [t for t in self.tools if t.name != name]

        # Remove from formatted tool list
        for i, desc in enumerate(self.tool_list):
            if (
                desc.get("type") == "api"
                and desc.get("function", {}).get("name") == name
            ):
                self.tool_list.pop(i)
                tool_found = True
                break

        if tool_found:
            # Save configuration
            self._save_yaml_tools()
            logger.info("Deleted custom tool, name: %s", name)
            return True
        else:
            logger.warning("Cannot find custom tool with name: %s", name)
            return False

    def get_custom_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get custom tool configuration

        Args:
            name: Tool name

        Returns:
            Tool configuration, or None if not found
        """
        for desc in self.tool_list:
            if (
                desc.get("type") == "api"
                and desc.get("function", {}).get("name") == name
            ):
                return desc
        logger.debug("Custom tool not found, Name: %s", name)
        return None

    def get_tools(self, filter: List[str] = None) -> List[Tool]:
        """
        Get list of all tool objects

        Returns:
            List of Tool objects
        """
        if filter:
            return [t for t in self.tools if t.name in filter]
        return self.tools

    def get_tool_list(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get tool list in the specified format

        Returns:
            {"toolList": [...]} format tool list
        """
        return {"toolList": self.tool_list}

    def get_tool_by_name(self, name: str) -> Optional[Tool]:
        """
        Get tool by name

        Args:
            name: Tool name

        Returns:
            Found tool, or None if not found
        """
        for tool in self.tools:
            if tool.name == name:
                return tool
        logger.debug("Tool not found, Name: %s", name)
        return None


tool_manager = ToolManager()
