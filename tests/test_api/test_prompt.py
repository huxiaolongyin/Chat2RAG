import pytest
from httpx import AsyncClient


@pytest.fixture
async def test_prompt(client: AsyncClient):
    """创建测试用提示词"""
    response = await client.post(
        "/api/v1/prompt/",
        json={
            "promptName": "测试提示词",
            "promptIntro": "测试提示词描述",
            "promptText": "这是测试提示词内容 {context} {question}",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "0000"
    return data["data"]


class TestPrompt:
    """提示词测试"""

    async def test_create_prompt_success(self, client: AsyncClient):
        """测试创建提示词成功"""
        response = await client.post(
            "/api/v1/prompt/",
            json={
                "promptName": "客服助手",
                "promptIntro": "客服对话助手提示词",
                "promptText": "你是一个专业的客服助手。根据以下上下文:\n{context}\n\n回答用户问题:\n{question}",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "promptId" in data["data"]
        assert "成功" in data["msg"]

    async def test_create_prompt_duplicate(self, client: AsyncClient, test_prompt):
        """测试创建重复提示词"""
        response = await client.post(
            "/api/v1/prompt/",
            json={
                "promptName": "测试提示词",
                "promptIntro": "重复描述",
                "promptText": "重复内容",
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "已存在" in data["msg"]

    async def test_get_prompt_list(self, client: AsyncClient, test_prompt):
        """测试获取提示词列表"""
        response = await client.get("/api/v1/prompt/")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "promptList" in data["data"]
        assert data["data"]["total"] >= 1
        assert len(data["data"]["promptList"]) >= 1

    async def test_get_prompt_list_with_search(self, client: AsyncClient, test_prompt):
        """测试搜索提示词列表"""
        # 按名称搜索
        response = await client.get("/api/v1/prompt/", params={"promptName": "测试"})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 1

        # 按描述搜索
        response = await client.get("/api/v1/prompt/", params={"promptDesc": "测试"})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 1

    async def test_get_prompt_list_pagination(self, client: AsyncClient):
        """测试提示词列表分页"""
        # 创建多个提示词
        for i in range(5):
            await client.post(
                "/api/v1/prompt/",
                json={
                    "promptName": f"提示词{i}",
                    "promptIntro": f"描述{i}",
                    "promptText": f"内容{i}",
                },
            )

        # 测试分页
        response = await client.get("/api/v1/prompt/", params={"current": 1, "size": 3})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert len(data["data"]["promptList"]) <= 3
        assert data["data"]["current"] == 1
        assert data["data"]["size"] == 3
        assert "pages" in data["data"]

    async def test_update_prompt_success(self, client: AsyncClient, test_prompt):
        """测试更新提示词成功"""
        prompt_id = test_prompt["promptId"]
        response = await client.put(
            f"/api/v1/prompt/{prompt_id}",
            json={
                "promptName": "更新后的提示词",
                "promptIntro": "更新后的描述",
                "promptText": "更新后的内容 {context} {question}",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["promptId"] == prompt_id
        assert "成功" in data["msg"]

    async def test_update_prompt_not_found(self, client: AsyncClient):
        """测试更新不存在的提示词"""
        response = await client.put(
            "/api/v1/prompt/99999",
            json={
                "promptName": "不存在的提示词",
                "promptIntro": "不存在",
                "promptText": "不存在",
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "不存在" in data["msg"]

    async def test_update_prompt_duplicate(self, client: AsyncClient):
        """测试更新提示词为重复名称"""
        # 创建两个提示词
        prompt1 = await client.post(
            "/api/v1/prompt/",
            json={
                "promptName": "提示词A",
                "promptIntro": "描述A",
                "promptText": "内容A",
            },
        )
        prompt1_data = prompt1.json()["data"]

        prompt2 = await client.post(
            "/api/v1/prompt/",
            json={
                "promptName": "提示词B",
                "promptIntro": "描述B",
                "promptText": "内容B",
            },
        )
        prompt2_data = prompt2.json()["data"]

        # 尝试将提示词B更新为提示词A的名称
        response = await client.put(
            f"/api/v1/prompt/{prompt2_data['promptId']}",
            json={
                "promptName": "提示词A",
                "promptIntro": "新描述",
                "promptText": "新内容",
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "已存在" in data["msg"]

    async def test_update_prompt_partial(self, client: AsyncClient, test_prompt):
        """测试部分更新提示词"""
        prompt_id = test_prompt["promptId"]
        # 只更新描述
        response = await client.put(
            f"/api/v1/prompt/{prompt_id}",
            json={
                "promptIntro": "只更新描述",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "成功" in data["msg"]

    async def test_delete_prompt_success(self, client: AsyncClient):
        """测试删除提示词成功"""
        # 创建提示词
        create_response = await client.post(
            "/api/v1/prompt/",
            json={
                "promptName": "待删除提示词",
                "promptIntro": "待删除",
                "promptText": "待删除内容",
            },
        )
        prompt_id = create_response.json()["data"]["promptId"]

        # 删除提示词
        response = await client.delete(f"/api/v1/prompt/{prompt_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "成功" in data["msg"]

    async def test_delete_prompt_not_found(self, client: AsyncClient):
        """测试删除不存在的提示词"""
        response = await client.delete("/api/v1/prompt/99999")
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "不存在" in data["msg"]

    async def test_default_prompt_creation(self, client: AsyncClient):
        """测试默认提示词自动创建"""
        # 第一次访问列表时应该创建默认提示词
        response = await client.get("/api/v1/prompt/")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"

        # 检查是否存在默认提示词
        prompt_list = data["data"]["promptList"]
        default_prompt = next(
            (p for p in prompt_list if p["promptName"] == "默认"), None
        )
        assert default_prompt is not None


class TestEdgeCases:
    """边界情况测试"""

    async def test_prompt_name_max_length(self, client: AsyncClient):
        """测试提示词名称长度限制"""
        response = await client.get("/api/v1/prompt/", params={"promptName": "a" * 51})
        # 应该会因为验证失败返回422
        assert response.status_code == 422

    async def test_prompt_desc_max_length(self, client: AsyncClient):
        """测试提示词描述长度限制"""
        response = await client.get("/api/v1/prompt/", params={"promptDesc": "a" * 51})
        # 应该会因为验证失败返回422
        assert response.status_code == 422

    async def test_empty_list(self, client: AsyncClient):
        """测试空列表"""
        response = await client.get(
            "/api/v1/prompt/",
            params={"promptName": "不存在的搜索词xyz123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] == 0
        assert len(data["data"]["promptList"]) == 0

    async def test_create_prompt_with_empty_name(self, client: AsyncClient):
        """测试创建空名称提示词"""
        response = await client.post(
            "/api/v1/prompt/",
            json={
                "promptName": "",
                "promptIntro": "描述",
                "promptText": "内容",
            },
        )

        # 应该会因为验证失败返回422
        assert response.status_code == 422

    async def test_create_prompt_with_empty_text(self, client: AsyncClient):
        """测试创建空内容提示词"""
        response = await client.post(
            "/api/v1/prompt/",
            json={
                "promptName": "测试名称",
                "promptIntro": "描述",
                "promptText": "",
            },
        )
        # 应该会因为验证失败返回422
        assert response.status_code == 422

    async def test_pagination_edge_cases(self, client: AsyncClient):
        """测试分页边界情况"""
        # 测试 current = 0
        response = await client.get(
            "/api/v1/prompt/", params={"current": 0, "size": 10}
        )
        assert response.status_code == 422

        # 测试 size = 0
        response = await client.get("/api/v1/prompt/", params={"current": 1, "size": 0})
        assert response.status_code == 422

        # 测试超大页码
        response = await client.get(
            "/api/v1/prompt/", params={"current": 9999, "size": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert len(data["data"]["promptList"]) == 0
