import requests
from config import CONFIG

MODEL_BASE_URL = "/api/v1/models"


class ModelController:
    def __init__(self):
        self.model_base_url = f"{CONFIG.BASE_URL}{MODEL_BASE_URL}/option"

    def get_model_list(self):
        response = requests.get(self.model_base_url)
        if response.status_code == 200:
            data = response.json()["data"]
            return [d["id"] for d in data]

        else:
            return []


model_controller = ModelController()
