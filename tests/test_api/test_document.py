import json
import os

import pytest
from httpx import AsyncClient

DOCUMENT_BASE_URL = "/api/v1/knowledge/collection"


@pytest.fixture
async def test_collection(client: AsyncClient):
    """创建测试用文档"""
    collection_name = "测试数据"
    response = await client.post(
        DOCUMENT_BASE_URL, params={"collectionName": collection_name}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "0000"

    # 返回集合名称供其他测试使用
    yield collection_name


@pytest.fixture
async def test_documents(client: AsyncClient, test_collection):
    """创建测试用文档"""
    response = await client.post(
        f"{DOCUMENT_BASE_URL}/document",
        params={"collectionName": test_collection},
        files={"file": open("tests/测试数据.csv", "rb")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "0000"

    response = await client.get(f"{DOCUMENT_BASE_URL}/document?collectionName=测试数据")
    assert response.status_code == 200
    return data["data"]


class TestCollection:
    """知识库集合测试"""

    async def test_create_collection(self, client: AsyncClient):
        """测试创建知识库"""
        collection_name = "新知识库"
        response = await client.post(
            DOCUMENT_BASE_URL,
            params={"collectionName": collection_name},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["msg"] == "知识库创建成功"

    async def test_get_collect_list(self, client: AsyncClient, test_collection):
        """测试获取知识库集合列表"""
        response = await client.get(DOCUMENT_BASE_URL)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "collectionList" in data["data"]
        assert data["data"]["total"] >= 1
        assert len(data["data"]["collectionList"]) >= 1

    async def test_get_prompt_list_with_search(
        self, client: AsyncClient, test_collection
    ):
        """测试搜索知识库集合列表"""
        # 按名称搜索
        response = await client.get(DOCUMENT_BASE_URL, params={"promptName": "测试"})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 1

    async def test_get_collection_list_with_pagination(
        self, client: AsyncClient, test_collection
    ):
        """测试分页获取知识库列表"""
        response = await client.get(DOCUMENT_BASE_URL, params={"current": 1, "size": 5})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["current"] == 1
        assert data["data"]["size"] == 5

    async def test_delete_collection(self, client: AsyncClient):
        """测试删除知识库"""
        # 先创建
        response = await client.post(
            DOCUMENT_BASE_URL, params={"collectionName": "待删除知识库"}
        )
        assert response.status_code == 200

        # 再删除
        response = await client.delete(
            DOCUMENT_BASE_URL, params={"collectionName": "待删除知识库"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["msg"] == "知识库删除成功"


class TestDocument:
    """知识文档测试"""

    async def test_create_documents(self, client: AsyncClient, test_collection):
        """测试创建知识"""
        response = await client.post(
            f"{DOCUMENT_BASE_URL}/document",
            params={"collectionName": test_collection},
            files={"file": open("tests/测试数据.csv", "rb")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["msg"] == "知识内容创建成功"
        assert "fileId" in data["data"]
        assert "chunkCount" in data["data"]

    async def test_get_documents(
        self, client: AsyncClient, test_collection, test_documents
    ):
        """测试获取知识库所有文档"""
        response = await client.get(
            f"{DOCUMENT_BASE_URL}/document", params={"collectionName": test_collection}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "docList" in data["data"]
        assert data["data"]["total"] >= 3
        assert len(data["data"]["docList"]) >= 3

    async def test_get_documents_with_pagination(
        self, client: AsyncClient, test_collection, test_documents
    ):
        """测试分页获取文档"""
        response = await client.get(
            f"{DOCUMENT_BASE_URL}/document",
            params={"collectionName": test_collection, "current": 1, "size": 2},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["current"] == 1
        assert data["data"]["size"] == 2
        assert len(data["data"]["docList"]) == 2

    async def test_get_documents_with_search(
        self, client: AsyncClient, test_collection, test_documents
    ):
        """测试搜索文档内容"""
        response = await client.get(
            f"{DOCUMENT_BASE_URL}/document",
            params={"collectionName": test_collection, "documentContent": "餐饮供应"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 1

    async def test_get_documents_with_sorting(
        self, client: AsyncClient, test_collection, test_documents
    ):
        """测试文档排序"""
        response = await client.get(
            f"{DOCUMENT_BASE_URL}/document",
            params={
                "collectionName": test_collection,
                "sortBy": "content",
                "sortOrder": "asc",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"

    async def test_delete_documents(
        self, client: AsyncClient, test_collection, test_documents
    ):
        """测试删除知识"""

        response = await client.get(
            f"{DOCUMENT_BASE_URL}/document",
            params={"collectionName": test_collection, "current": 1, "size": 2},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        doc_list = data["data"]["docList"]

        response = await client.request(
            "DELETE",
            f"{DOCUMENT_BASE_URL}/document",
            params={"collectionName": test_collection},
            json=[doc_list[0]["id"]],
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["msg"] == "删除知识成功"


class TestQuery:
    """知识查询测试"""

    async def test_query_documents(
        self, client: AsyncClient, test_collection, test_documents
    ):
        """测试知识内容查询"""
        response = await client.get(
            f"{DOCUMENT_BASE_URL.replace('/collection', '')}/query",
            params={
                "collectionName": test_collection,
                "query": "Python",
                "topK": 5,
                "type": "qa_pair",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "docList" in data["data"]
        assert data["data"]["topK"] == 5

    async def test_query_documents_with_threshold(
        self, client: AsyncClient, test_collection, test_documents
    ):
        """测试带阈值的查询"""
        response = await client.get(
            f"{DOCUMENT_BASE_URL.replace('/collection', '')}/query",
            params={
                "collectionName": test_collection,
                "query": "编程",
                "topK": 3,
                "scoreThreshold": 0.7,
                "type": "question",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["scoreThreshold"] == 0.7

    async def test_exact_query(
        self, client: AsyncClient, test_collection, test_documents
    ):
        """测试精确查询"""
        response = await client.get(
            f"{DOCUMENT_BASE_URL.replace('/collection', '')}/exact-query",
            params={"collectionName": test_collection, "query": "Python是什么"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "answer" in data["data"]

    async def test_exact_query_no_result(
        self, client: AsyncClient, test_collection, test_documents
    ):
        """测试精确查询无结果情况"""
        response = await client.get(
            f"{DOCUMENT_BASE_URL.replace('/collection', '')}/exact-query",
            params={"collectionName": test_collection, "query": "不存在的问题"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["answer"] is None
