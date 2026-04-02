import json
from typing import Dict

from haystack.dataclasses import StreamingChunk

from chat2rag.core.logger import get_logger
from chat2rag.schemas.chat import SourceType

logger = get_logger(__name__)


class ToolCallHandler:
    def __init__(self):
        self._executed_tools: list[str] = []
        self._tool_sources: Dict[str, str] = {}
        self._tool_calls_cache: Dict[str, dict] = {}
        self._seen_tools: set[str] = set()

    def handle_tool_call(self, chunk: StreamingChunk) -> tuple[str, dict, dict]:
        tool_call = chunk.meta.get("tool_call", {})
        tool_result = chunk.meta.get("tool_result", {})

        tool_name = ""
        arguments = {}

        if tool_call:
            tool_name = tool_call.tool_name
            arguments = tool_call.arguments

            self._add_executed_tool(tool_name)

            if arguments:
                self._tool_calls_cache[tool_name] = {
                    "arguments": arguments,
                }

        parsed_result = {}
        if tool_result:
            parsed_result = self._parse_tool_result(str(tool_result))

        return tool_name, arguments, parsed_result

    def _parse_tool_result(self, tool_result: str) -> dict:
        try:
            parsed = json.loads(tool_result)

            if isinstance(parsed, dict) and "content" in parsed:
                content = parsed.get("content")

                if isinstance(content, list) and len(content) > 0:
                    first_content = content[0]

                    if isinstance(first_content, dict) and "text" in first_content:
                        try:
                            inner_text = first_content["text"]
                            first_content["text"] = json.loads(inner_text)
                        except json.JSONDecodeError:
                            pass

                    parsed["content"] = first_content

            return parsed

        except json.JSONDecodeError:
            logger.warning(f"Failed to parse tool result as JSON: {tool_result[:100]}")
            return {}
        except Exception:
            logger.exception("Error parsing tool result")
            return {}

    def _add_executed_tool(self, tool_name: str):
        if tool_name in self._seen_tools:
            return

        self._seen_tools.add(tool_name)
        self._executed_tools.append(tool_name)

    def set_tool_sources(self, sources: Dict[str, str]):
        self._tool_sources = sources

    def get_executed_tools(self) -> list[str]:
        return self._executed_tools.copy()

    def get_tool_sources(self) -> Dict[str, str]:
        return self._tool_sources.copy()

    def generate_source_items(self) -> list[dict]:
        source_items = []

        for tool_name in self._executed_tools:
            server_name = self._tool_sources.get(tool_name, "")
            detail = f"server: {server_name}" if server_name else ""

            source_items.append(
                {
                    "type": SourceType.TOOL,
                    "display": tool_name,
                    "detail": detail,
                }
            )

        return source_items

    def clear(self):
        self._executed_tools.clear()
        self._tool_sources.clear()
        self._tool_calls_cache.clear()
        self._seen_tools.clear()

    def get_tool_call_cache(self, tool_name: str) -> dict | None:
        return self._tool_calls_cache.get(tool_name)
