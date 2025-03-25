import requests
from config import CONFIG


class ModelController:
    def __init__(self):
        self.model_base_url = (
            f"http://{CONFIG.BACKEND_HOST}:{CONFIG.BACKEND_PORT}/api/v1/model/list"
        )

    def get_model_list(self):
        response = requests.get(
            self.model_base_url,
        )
        if response.status_code == 200:
            models = response.json()["data"]
            return [item["id"] for item in models]
        else:
            return []


model_controller = ModelController()
