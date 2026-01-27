import requests
from config import CONFIG


class MetricController:
    def __init__(self):
        self.metric_base_url = f"{CONFIG.BASE_URL}/api/v1/metrics"

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
            return response.json()["data"]["items"]
        else:
            return []

    def get_hot_questions(self, collection: str | None = None, days: int = 30, limit: int = 10):
        response = requests.get(
            f"{self.metric_base_url}/hot-questions",
            params={"collection": collection, "days": days, "limit": limit},
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()
        if result["code"] == "0000" and result["data"]:
            return result["data"]


metric_controller = MetricController()
