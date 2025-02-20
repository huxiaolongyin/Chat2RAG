import requests
from config import CONFIG


class PromptController:
    def __init__(self):
        self.prompt_base_url = (
            f"http://{CONFIG.BACKEND_HOST}:{CONFIG.BACKEND_PORT}/api/v1/prompt/list"
        )
        self.prompt_create_url = (
            f"http://{CONFIG.BACKEND_HOST}:{CONFIG.BACKEND_PORT}/api/v1/prompt/add"
        )
        self.prompt_update_url = (
            f"http://{CONFIG.BACKEND_HOST}:{CONFIG.BACKEND_PORT}/api/v1/prompt/update"
        )
        self.prompt_delete_url = (
            f"http://{CONFIG.BACKEND_HOST}:{CONFIG.BACKEND_PORT}/api/v1/prompt/remove"
        )

    def get_prompt_name_list(self):
        """获取提示词名称列表"""
        response = requests.get(
            self.prompt_base_url, params={"current": 1, "size": 100}
        )
        if response.status_code == 200:
            result = response.json()["data"]["promptList"]
            return [item["promptName"] for item in result]
        else:
            return []

    def get_prompt_list(self):
        """获取提示词列表"""
        response = requests.get(
            self.prompt_base_url, params={"current": 1, "size": 100}
        )
        if response.status_code == 200:
            return response.json()["data"]["promptList"]
        else:
            return []

    def create_prompt(self, prompt_name: str, prompt_intro: str, prompt_text: str):
        """创建提示词"""
        data = {
            "promptName": prompt_name,
            "promptIntro": prompt_intro,
            "promptText": prompt_text,
        }
        response = requests.post(self.prompt_create_url, json=data)
        if response.status_code == 200:
            return response.json()
        else:
            return None

    def update_prompt(
        self, prompt_id: int, prompt_name: str, prompt_intro: str, prompt_text: str
    ):
        """更新提示词"""
        data = {
            "promptName": prompt_name,
            "promptIntro": prompt_intro,
            "promptText": prompt_text,
        }
        response = requests.put(
            self.prompt_update_url, params={"promptId": prompt_id}, json=data
        )
        if response.status_code == 200:
            return response.json()
        else:
            return None

    def delete_prompt(self, prompt_id):
        """删除提示词"""
        response = requests.delete(
            self.prompt_delete_url, params={"promptId": prompt_id}
        )
        if response.status_code == 200:
            return response.json()
        else:
            return None


prompt_controller = PromptController()
