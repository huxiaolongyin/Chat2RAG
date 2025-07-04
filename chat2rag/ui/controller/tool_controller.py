import requests
from config import CONFIG


class ToolController:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.too_base_url = (
            f"http://{CONFIG.BACKEND_HOST}:{CONFIG.BACKEND_PORT}/api/v1/tools"
        )
        self.tools = self.fetch_tools()

    def fetch_tools(self) -> dict:
        response = requests.get(
            self.too_base_url + "/list", params={"current": 1, "size": 100}
        )
        if response.status_code == 200:
            result = response.json()["data"]["toolList"]
            return {
                item["function"]["displayName"]: item["function"]["name"]
                for item in result
                if item["function"]["name"] != "web_search"
            }
        else:
            return {}

    def del_tool(self, tool_name: str):
        requests.delete(
            self.too_base_url + "/remove",
            params={"toolName": tool_name},
        )

    # def add_tool(self, tool_name: str, tool_content: str):
    #     requests.post(
    #         self.too_base_url + "/add",
    #         json={"toolName": tool_name, "toolContent": tool_content},
    #     )
    #         params={"collectionName": collection_name},
    #         json=[asdict(doc) for doc in document],
    #     )


tool_controller = ToolController()
