from haystack_integrations.tools.mcp import MCPTool, SSEServerInfo

from chat2rag.config import CONFIG

server_info = SSEServerInfo(url=f"https://mcp.amap.com/sse?key={CONFIG.GAODE_API_KEY}")
get_weather_info = MCPTool(name="maps_weather", server_info=server_info)
