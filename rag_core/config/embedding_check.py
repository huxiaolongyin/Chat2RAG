import time
from threading import Lock, Thread

import requests
from requests.exceptions import RequestException

from rag_core.logging import logger


class EmbeddingUrlMonitor:
    _instance = None
    _lock = Lock()
    _initialized = False

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # 防止重复初始化
        if hasattr(self, "_initialized") and self._initialized:
            return

        with self._lock:
            if self._initialized:
                return
            # 设置默认值
            self.local_url = None
            self.remote_url = None
            self.current_url = None
            self.is_remote_healthy = True
            self.retry_count = 3
            self.retry_delay = 1
            self.check_interval = 30
            self.monitor_thread = None
            self._initialized = True

    def setup(self, local_url: str, remote_url: str):
        """配置URL并启动监控"""
        with self._lock:
            self.local_url = local_url
            self.remote_url = remote_url
            self.current_url = remote_url

            if not self.monitor_thread:
                self.monitor_thread = Thread(
                    target=self._health_check_loop, daemon=True
                )
                self.monitor_thread.start()

    @classmethod
    def get_instance(cls):
        return cls()

    def _check_single_url(self, url: str) -> bool:
        """
        单次URL检查
        """
        process_url = url.replace("v1", "") + "status"
        try:
            response = requests.get(process_url, timeout=3)
            if response.status_code == 200:
                logger.info(f"Embedding service url <{url}> is healthy.")
                return True
        except (requests.ConnectionError, requests.Timeout, RequestException) as e:
            logger.warning(f"Embedding service url <{url}> request failed: {str(e)}")
        return False

    def check_url_health(self, url: str) -> bool:
        """
        带重试的URL健康检查
        """
        logger.info("Embedding service healthy checking...")

        # 第一次检查
        if self._check_single_url(url):
            return True

        # 失败后进行重试
        for attempt in range(1, self.retry_count):
            logger.warning(f"Retry attempt {attempt}/{self.retry_count-1}...")
            time.sleep(self.retry_delay)
            if self._check_single_url(url):
                return True

        logger.error(
            f"Embedding service url <{url}> is unhealthy. Please check the service."
        )
        return False

    def _health_check_loop(self):
        """
        持续运行的健康检查循环
        """
        while True:
            remote_health = self.check_url_health(self.remote_url)

            if remote_health != self.is_remote_healthy:
                self.is_remote_healthy = remote_health
                self.current_url = self.remote_url if remote_health else self.local_url
                logger.warning(
                    f"Change Embedding service to {'Remote' if remote_health else 'Loacl'}; Service url: {self.current_url}"
                )

            time.sleep(self.check_interval)

    def get_current_url(self) -> str:
        """
        获取当前可用的URL
        """
        return self.current_url
