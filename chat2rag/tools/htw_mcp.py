from haystack_integrations.tools.mcp import MCPTool, SSEServerInfo

server_info = SSEServerInfo(url="http://localhost:8333/sse")
lead_way_tool = MCPTool(name="lead_way", server_info=server_info)
