import requests
from config import CONFIG


class ModelController:
    def __init__(self):
        self.model_base_url = f"http://127.0.0.1:8000/api/v1/model/list"

    def get_model_list(self):
        response = requests.get(
            self.model_base_url,
        )
        if response.status_code == 200:
            models = response.json()["data"]
            return [item["name"] for item in models]
        else:
            return []


model_controller = ModelController()
