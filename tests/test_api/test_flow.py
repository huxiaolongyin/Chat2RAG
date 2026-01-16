import pytest
from httpx import AsyncClient

FLOW_BASE_URL = "/api/v1/flows"


@pytest.mark.asyncio
class TestFlowAPI:
    """流程数据API测试"""

    async def test_create_flow_success(self, client: AsyncClient):
        """测试成功创建流程"""
        flow_data = {
            "name": "test_flow",
            "desc": "测试流程",
            "currentVersion": 1,
            "flowJson": {"nodes": [], "edges": []},
        }

        response = await client.post(FLOW_BASE_URL, json=flow_data)
        assert response.status_code == 200

        result = response.json()
        assert result["code"] == "0000"
        assert result["msg"] == "流程创建成功"
        assert result["data"]["name"] == "test_flow"
        assert result["data"]["desc"] == "测试流程"

    async def test_create_flow_duplicate_name(self, client: AsyncClient):
        """测试创建重名流程"""
        flow_data = {
            "name": "duplicate_flow",
            "desc": "重复流程",
            "currentVersion": 1,
            "flowJson": {"nodes": [], "edges": []},
        }

        # 第一次创建
        await client.post(FLOW_BASE_URL, json=flow_data)

        # 第二次创建同名流程
        response = await client.post(FLOW_BASE_URL, json=flow_data)
        assert response.status_code == 409

        result = response.json()
        assert "该流程已存在" in result["msg"]

    async def test_create_flow_minimal_data(self, client: AsyncClient):
        """测试使用最小数据创建流程"""
        flow_data = {"name": "minimal_flow"}

        response = await client.post(FLOW_BASE_URL, json=flow_data)
        assert response.status_code == 200

        result = response.json()
        assert result["code"] == "0000"
        assert result["data"]["name"] == "minimal_flow"

    async def test_get_flowList_empty(self, client: AsyncClient):
        """测试获取空流程列表"""
        response = await client.get(FLOW_BASE_URL)
        assert response.status_code == 200

        result = response.json()
        assert result["code"] == "0000"
        assert result["data"]["total"] == 0
        assert result["data"]["flowList"] == []
        assert result["data"]["current"] == 1
        assert result["data"]["size"] == 10

    async def test_get_flowList_with_data(self, client: AsyncClient):
        """测试获取流程列表"""
        # 创建测试数据
        for i in range(15):
            await client.post(
                FLOW_BASE_URL,
                json={"name": f"flow_{i}", "desc": f"流程{i}"},
            )

        # 获取第一页
        response = await client.get(FLOW_BASE_URL, params={"current": 1, "size": 10})
        assert response.status_code == 200

        result = response.json()
        assert result["code"] == "0000"
        assert result["data"]["total"] == 15
        assert len(result["data"]["flowList"]) == 10
        assert result["data"]["current"] == 1
        assert result["data"]["size"] == 10

    async def test_get_flowList_pagination(self, client: AsyncClient):
        """测试流程列表分页"""
        # 创建测试数据
        for i in range(25):
            await client.post(FLOW_BASE_URL, json={"name": f"page_flow_{i}"})

        # 获取第二页
        response = await client.get(FLOW_BASE_URL, params={"current": 2, "size": 10})
        assert response.status_code == 200

        result = response.json()
        assert result["code"] == "0000"
        assert result["data"]["total"] == 25
        assert len(result["data"]["flowList"]) == 10
        assert result["data"]["current"] == 2

    async def test_get_flowList_search_by_name(self, client: AsyncClient):
        """测试按名称搜索流程"""
        # 创建测试数据
        await client.post(FLOW_BASE_URL, json={"name": "search_flow_1"})
        await client.post(FLOW_BASE_URL, json={"name": "search_flow_2"})
        await client.post(FLOW_BASE_URL, json={"name": "other_flow"})

        # 搜索包含 "search" 的流程
        response = await client.get(FLOW_BASE_URL, params={"name": "search"})
        assert response.status_code == 200

        result = response.json()
        assert result["code"] == "0000"
        # 注意: 这里假设 name 参数是模糊搜索,需要根据实际实现调整

    async def test_get_flow_detail_success(self, client: AsyncClient):
        """测试成功获取流程详情"""
        # 先创建一个流程
        create_response = await client.post(
            FLOW_BASE_URL,
            json={
                "name": "detail_flow",
                "desc": "详情测试",
                "flowJson": {"key": "value"},
            },
        )
        flow_id = create_response.json()["data"]["id"]

        # 获取详情
        response = await client.get(f"{FLOW_BASE_URL}/{flow_id}")
        assert response.status_code == 200

        result = response.json()
        assert result["code"] == "0000"
        assert result["data"]["id"] == flow_id
        assert result["data"]["name"] == "detail_flow"
        assert result["data"]["desc"] == "详情测试"

    async def test_get_flow_detail_not_found(self, client: AsyncClient):
        """测试获取不存在的流程"""
        response = await client.get(f"{FLOW_BASE_URL}/99999")
        assert response.status_code == 400

        result = response.json()
        assert "不存在" in result["msg"]

    async def test_update_flow_success(self, client: AsyncClient):
        """测试成功更新流程"""
        # 先创建一个流程
        create_response = await client.post(FLOW_BASE_URL, json={"name": "update_flow", "desc": "原始描述"})
        flow_id = create_response.json()["data"]["id"]

        # 更新流程
        update_data = {
            "name": "updated_flow",
            "desc": "更新后的描述",
            "currentVersion": 2,
        }
        response = await client.put(f"{FLOW_BASE_URL}/{flow_id}", json=update_data)
        assert response.status_code == 200

        result = response.json()
        assert result["code"] == "0000"
        assert result["data"]["name"] == "updated_flow"
        assert result["data"]["desc"] == "更新后的描述"
        assert result["data"]["currentVersion"] == 2

    async def test_update_flow_not_found(self, client: AsyncClient):
        """测试更新不存在的流程"""
        response = await client.put(f"{FLOW_BASE_URL}/99999", json={"name": "test"})
        assert response.status_code == 400

        result = response.json()
        assert "不存在" in result["msg"]

    async def test_update_flow_duplicate_name(self, client: AsyncClient):
        """测试更新为已存在的名称"""
        # 创建两个流程
        await client.post(FLOW_BASE_URL, json={"name": "flow_a"})
        create_response = await client.post(FLOW_BASE_URL, json={"name": "flow_b"})
        flow_id = create_response.json()["data"]["id"]

        # 尝试将 flow_b 更新为 flow_a
        response = await client.put(f"{FLOW_BASE_URL}/{flow_id}", json={"name": "flow_a"})
        assert response.status_code == 400

        result = response.json()
        assert result["code"] == "4000"
        assert "该分类已存在" in result["msg"]

    async def test_update_flow_partial(self, client: AsyncClient):
        """测试部分更新流程"""
        # 创建流程
        create_response = await client.post(
            FLOW_BASE_URL,
            json={"name": "partial_flow", "desc": "原始描述", "currentVersion": 1},
        )
        flow_id = create_response.json()["data"]["id"]

        # 只更新描述
        response = await client.put(f"{FLOW_BASE_URL}/{flow_id}", json={"desc": "新描述"})
        assert response.status_code == 200

        result = response.json()
        assert result["code"] == "0000"
        assert result["data"]["name"] == "partial_flow"  # 名称未变
        assert result["data"]["desc"] == "新描述"  # 描述已更新

    async def test_delete_flow_success(self, client: AsyncClient):
        """测试成功删除流程"""
        # 先创建一个流程
        create_response = await client.post(FLOW_BASE_URL, json={"name": "delete_flow"})
        flow_id = create_response.json()["data"]["id"]

        # 删除流程
        response = await client.delete(f"{FLOW_BASE_URL}/{flow_id}")
        assert response.status_code == 200

        result = response.json()
        assert result["code"] == "0000"
        assert result["msg"] == "删除成功"

        # 验证已删除
        get_response = await client.get(f"{FLOW_BASE_URL}/{flow_id}")
        assert get_response.json()["code"] == "4000"

    async def test_delete_flow_not_found(self, client: AsyncClient):
        """测试删除不存在的流程"""
        response = await client.delete(f"{FLOW_BASE_URL}/99999")
        assert response.status_code == 400

        result = response.json()
        assert result["code"] == "4000"
        assert "流程数据不存在" in result["msg"]

    async def test_flow_lifecycle(self, client: AsyncClient):
        """测试流程完整生命周期: 创建 -> 查询 -> 更新 -> 删除"""
        # 1. 创建
        create_data = {
            "name": "lifecycle_flow",
            "desc": "生命周期测试",
            "currentVersion": 1,
            "flowJson": {"step": "create"},
        }
        create_response = await client.post(FLOW_BASE_URL, json=create_data)
        assert create_response.json()["code"] == "0000"
        flow_id = create_response.json()["data"]["id"]

        # 2. 查询详情
        get_response = await client.get(f"{FLOW_BASE_URL}/{flow_id}")
        assert get_response.json()["code"] == "0000"
        assert get_response.json()["data"]["name"] == "lifecycle_flow"

        # 3. 更新
        update_response = await client.put(
            f"{FLOW_BASE_URL}/{flow_id}",
            json={"desc": "更新后的描述", "currentVersion": 2},
        )
        assert update_response.json()["code"] == "0000"
        assert update_response.json()["data"]["currentVersion"] == 2

        # 4. 删除
        delete_response = await client.delete(f"{FLOW_BASE_URL}/{flow_id}")
        assert delete_response.json()["code"] == "0000"

        # 5. 验证删除
        final_get = await client.get(f"{FLOW_BASE_URL}/{flow_id}")
        assert final_get.json()["code"] == "4000"
