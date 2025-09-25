import requests
from config import CONFIG


class MetricController:
    def __init__(self):
        self.metric_base_url = f"http://127.0.0.1:8000/api/v1/metrics/list"

    def get_metric_list(
        self,
        current: int = 1,
        size: int = 10,
        start_time: str = "2023-01-01",
        end_time: str = "2026-01-01",
        collection: str = "",
    ):
        """获取指标列表"""
        response = requests.get(
            self.metric_base_url,
            params={
                "current": current,
                "size": size,
                "startTime": start_time,
                "endTime": end_time,
                "collection": collection,
            },
        )
        if response.status_code == 200:
            return response.json()["data"]
        else:
            return []


metric_controller = MetricController()
