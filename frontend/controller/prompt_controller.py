import requests
from config import CONFIG


class PromptController:
    def __init__(self):
        self.prompt_base_url = (
            f"http://{CONFIG.BACKEND_HOST}:{CONFIG.BACKEND_PORT}/api/v1/prompt/list"
        )

    def get_prompt_name_list(self):
        response = requests.get(
            self.prompt_base_url, params={"current": 1, "size": 100}
        )
        if response.status_code == 200:
            result = response.json()["data"]["promptList"]
            return [item["promptName"] for item in result]
        else:
            return []

    def get_prompt_list(self):
        response = requests.get(
            self.prompt_base_url, params={"current": 1, "size": 100}
        )
        if response.status_code == 200:
            return response.json()["data"]["promptList"]
        else:
            return []


prompt_controller = PromptController()
