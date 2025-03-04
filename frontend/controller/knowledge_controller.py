import logging
from dataclasses import asdict
from typing import List

import requests
from config import CONFIG
from dataclass.document import QADocument


class KnowledgeController:
    def __init__(self):
        self.collect_base_url = f"http://{CONFIG.BACKEND_HOST}:{CONFIG.BACKEND_PORT}/api/v1/knowledge/collection"
        self.doc_base_url = f"http://{CONFIG.BACKEND_HOST}:{CONFIG.BACKEND_PORT}/api/v1/knowledge/collection/document"
        self.doc_query_url = (
            f"http://{CONFIG.BACKEND_HOST}:{CONFIG.BACKEND_PORT}/api/v1/knowledge/query"
        )

    def get_collection_list(self) -> List:
        response = requests.get(
            self.collect_base_url, params={"current": 1, "size": 100}
        )
        if response.status_code == 200:
            result = response.json()["data"]["collectionList"]
            return [item["collectionName"] for item in result]
        else:
            return []

    def del_collection(self, collection_name: str):
        requests.delete(
            self.collect_base_url,
            params={"collectionName": collection_name},
        )

    def get_documents(
        self,
        collection_name: str,
        current: int = 1,
        size: int = 10,
        document_content: str = None,
    ) -> tuple:
        response = requests.get(
            self.doc_base_url,
            params={
                "collectionName": collection_name,
                "current": current,
                "size": size,
                "documentContent": document_content,
            },
        )
        if response.status_code == 200:
            doc_list = response.json()["data"]["docList"]
            doc_total = response.json()["data"]["total"]
            return doc_list, doc_total
        else:
            return [], 0

    def add_document(self, collection_name: str, document: List[QADocument]):
        requests.post(
            self.doc_base_url,
            params={"collectionName": collection_name},
            json=[asdict(doc) for doc in document],
        )

    def delete_documents(self, collection_name: str, document_id: List[str]):
        requests.delete(
            self.doc_base_url,
            params={"collectionName": collection_name},
            json=document_id,
        )

    def query_document(self, collection_name: str, query: str, precision_mode: bool):
        """
        获取引用文档
        """
        try:
            # 精确模式查询
            if precision_mode:
                params = {
                    "collectionName": collection_name,
                    "query": query,
                    "type": "question",
                    # "scoreThreshold": 0.88,  # todo: 提到 env 处理
                }
                response = requests.get(self.doc_query_url, params=params, timeout=10)
                response_data = response.json()

                # 如果精确查询没有结果，自动降级到模糊查询
                if response.status_code == 200 and not response_data.get(
                    "data", {}
                ).get("docList", []):
                    precision_mode = False

            # 模糊查询
            if not precision_mode:
                params = {
                    "collectionName": collection_name,
                    "query": query,
                    "type": "qa_pair",
                }
                response = requests.get(self.doc_query_url, params=params, timeout=10)
                response_data = response.json()

            # 处理结果
            if response.status_code == 200:
                return response_data.get("data", {}).get("docList", [])
            else:
                logging.warning(
                    f"Query document failed with status code: {response.status_code}"
                )
                return []

        except requests.exceptions.RequestException as e:
            logging.error(f"Request error when querying document: {str(e)}")
            return []
        except (ValueError, KeyError) as e:
            logging.error(f"Error parsing response: {str(e)}")
            return []


knowledge_controller = KnowledgeController()
