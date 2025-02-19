import requests
from config import CONFIG


class ModelController:
    def __init__(self):
        self.model_base_url = f"{CONFIG.OPEN_BASE_URL}/models"
        self.token = CONFIG.API_TOKEN

    def get_model_list(self):
        headers = {"Authorization": "Bearer " + self.token}
        response = requests.get(self.model_base_url, headers=headers)
        if response.status_code == 200:
            models = response.json()["data"]
            return [item["id"] for item in models]
        else:
            return []


model_controller = ModelController()
