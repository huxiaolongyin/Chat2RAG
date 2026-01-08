import pytest
from httpx import AsyncClient

# API 的基础路径
ACTION_BASE_URL = "/api/v1/action"


@pytest.fixture
async def sample_action(client: AsyncClient):
    """创建测试用的机器人动作 Fixture"""
    payload = {
        "name": "测试动作_Fixture",
        "code": "TestFixtureCode",
        "description": "由Fixture创建",
        "isActive": True,
    }
    response = await client.post(ACTION_BASE_URL, json=payload)
    assert response.status_code == 200
    data = response.json()
    return data["data"]


class TestRobotAction:
    """机器人动作管理 API 测试"""

    async def test_create_action_success(self, client: AsyncClient):
        """测试成功创建动作"""
        payload = {
            "name": "挥手",
            "code": "WaveHands",
            "description": "机器人挥手动作",
            "isActive": True,
        }
        response = await client.post(ACTION_BASE_URL, json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["name"] == payload["name"]
        assert data["data"]["code"] == payload["code"]
        assert "id" in data["data"]

    async def test_create_action_validation_error(self, client: AsyncClient):
        """测试创建动作参数校验（必填项缺失）"""
        payload = {"name": "缺少代码"}
        response = await client.post(ACTION_BASE_URL, json=payload)

        assert response.status_code == 422
        # 验证是哪个字段报错
        detail = response.json()["detail"]
        assert any(err["loc"][-1] == "code" for err in detail)

    async def test_get_action_detail(self, client: AsyncClient, sample_action):
        """测试获取动作详情"""
        action_id = sample_action["id"]
        response = await client.get(f"{ACTION_BASE_URL}/{action_id}")

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == action_id
        assert data["name"] == sample_action["name"]

    async def test_get_action_detail_not_found(self, client: AsyncClient):
        """测试获取不存在的动作"""
        response = await client.get(f"{ACTION_BASE_URL}/999999")
        assert response.status_code == 404

    async def test_update_action(self, client: AsyncClient, sample_action):
        """测试更新动作"""
        action_id = sample_action["id"]

        # 注意: Schema 中 isActive 的 alias 是 "isActive"
        update_payload = {"name": "更新后的名称", "isActive": False}

        response = await client.put(f"{ACTION_BASE_URL}/{action_id}", json=update_payload)

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == "更新后的名称"
        assert data["isActive"] is False
        # 确认未修改的字段保持原样
        assert data["code"] == sample_action["code"]

    async def test_delete_action(self, client: AsyncClient, sample_action):
        """测试删除动作"""
        action_id = sample_action["id"]

        # 执行删除
        del_response = await client.delete(f"{ACTION_BASE_URL}/{action_id}")
        assert del_response.status_code == 200

        # 再次查询确认已删除
        get_response = await client.get(f"{ACTION_BASE_URL}/{action_id}")
        assert get_response.status_code in [404, 500]

    async def test_get_list_pagination_and_filter(self, client: AsyncClient):
        """测试列表分页与过滤功能"""
        # 1. 准备数据：创建两个具有特定特征的动作
        payload1 = {"name": "搜索测试A", "code": "SearchA", "isActive": True}
        payload2 = {"name": "搜索测试B", "code": "SearchB", "isActive": False}

        await client.post(ACTION_BASE_URL, json=payload1)
        await client.post(ACTION_BASE_URL, json=payload2)

        # 2. 测试 nameOrCode 过滤
        response = await client.get(ACTION_BASE_URL, params={"nameOrCode": "SearchA"})
        assert response.status_code == 200
        data = response.json()["data"]
        # 应该能搜到 A，但搜不到 B
        names = [item["name"] for item in data["list"]]
        assert "搜索测试A" in names
        assert "搜索测试B" not in names

        # 3. 测试 isActive 过滤 (注意 Query alias 是 isActive)
        response_active = await client.get(ACTION_BASE_URL, params={"isActive": False, "nameOrCode": "Search"})
        data_active = response_active.json()["data"]
        # 应该只返回 SearchB (isActive=False)
        assert len(data_active["list"]) >= 1
        assert all(item["isActive"] is False for item in data_active["list"])

        # 4. 测试分页
        # 假设至少有2条数据，每页取1条
        response_page = await client.get(ACTION_BASE_URL, params={"current": 1, "size": 1})
        data_page = response_page.json()["data"]
        assert len(data_page["list"]) == 1
        assert data_page["total"] >= 2
        assert data_page["size"] == 1
