from httpx import AsyncClient


class TestDocument:
    "知识库测试"

    async def test_get_collect_list(self, client: AsyncClient):
        """测试获取知识库集合列表"""
        response = await client.get("/api/v1/knowledge/collection")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "collectionList" in data["data"]
        assert data["data"]["total"] >= 1
        assert len(data["data"]["collectionList"]) >= 1

    async def test_get_prompt_list_with_search(self, client: AsyncClient):
        # TODO: 需要模拟qdant
        """测试搜索知识库集合列表"""
        # 按名称搜索
        response = await client.get(
            "/api/v1/knowledge/collection", params={"promptName": "测试"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 1

        # 按描述搜索
        response = await client.get(
            "/api/v1/knowledge/collection", params={"promptDesc": "测试"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 1
