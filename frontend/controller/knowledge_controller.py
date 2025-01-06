import os
from typing import List

import pandas as pd
import requests

BACKEND_HOST = os.environ.get("BACKEND_HOST", "host.docker.internal")
BACKEND_PORT = os.environ.get("BACKEND_PORT", "8000")


class KnowledgeController:
    def __init__(self):
        self.collect_base_url = (
            f"http://{BACKEND_HOST}:{BACKEND_PORT}/api/v1/knowledge/collection"
        )
        self.doc_base_url = (
            f"http://{BACKEND_HOST}:{BACKEND_PORT}/api/v1/knowledge/collection/document"
        )
        self.doc_query_url = (
            f"http://{BACKEND_HOST}:{BACKEND_PORT}/api/v1/knowledge/query"
        )

    def get_collections(self):
        response = requests.get(
            self.collect_base_url, params={"current": 1, "size": 100}
        )
        print()
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
    ) -> list:
        response = requests.get(
            self.doc_base_url,
            params={
                "collectionName": collection_name,
                "current": current,
                "size": size,
            },
        )
        if response.status_code == 200:
            doc_list = response.json()["data"]["docList"]
            doc_total = response.json()["data"]["total"]
            return doc_list, doc_total
        else:
            return [], 0

    def add_document(self, collection_name: str, document: List[str]):
        requests.post(
            self.doc_base_url,
            params={"collectionName": collection_name},
            json=document,
        )

    def delete_documents(self, collection_name: str, document_id: List[str]):
        requests.delete(
            self.doc_base_url,
            params={"collectionName": collection_name},
            json=document_id,
        )

    def query_document(self, collection_name: str, query: str):
        """
        获取引用文档
        """
        response = requests.get(
            self.doc_query_url,
            params={
                "collectionName": collection_name,
                "query": query,
            },
        )
        if response.status_code == 200:
            return response.json()["data"]["docList"]
        else:
            return []


knowledge_controller = KnowledgeController()
