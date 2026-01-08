import pytest
from httpx import AsyncClient

EXPRESSION_BASE_URL = "/api/v1/expressions"


@pytest.fixture
async def sample_expressions(client: AsyncClient):
    """创建测试用的机器人表情数据"""
    expressions = []
    # 创建多个测试表情
    expression_data = [
        {"name": "开心", "code": "happy", "description": "开心的表情", "isActive": True},
        {"name": "难过", "code": "sad", "description": "难过的表情", "isActive": True},
        {"name": "愤怒", "code": "angry", "description": "愤怒的表情", "isActive": False},
    ]

    for data in expression_data:
        expression = await client.post(EXPRESSION_BASE_URL, json=data)
        assert expression.status_code == 200
        expressions.append(expression)

    return expressions


class TestRobotExpressionAPI:
    """机器人表情 API 测试类"""

    async def test_get_expression_list_default(self, client: AsyncClient, sample_expressions):
        """测试获取表情列表 - 默认参数"""
        response = await client.get(EXPRESSION_BASE_URL)

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        expected_keys = {"items", "total", "current", "size"}
        assert expected_keys.issubset(data["data"].keys())
        assert data["data"]["current"] == 1
        assert data["data"]["size"] == 10

    async def test_get_expression_list_with_pagination(self, client: AsyncClient, sample_expressions):
        """测试获取表情列表 - 分页参数"""
        response = await client.get(f"{EXPRESSION_BASE_URL}?current=1&size=2")

        assert response.status_code == 200
        data = response.json()

        assert data["data"]["current"] == 1
        assert data["data"]["size"] == 2
        assert len(data["data"]["items"]) <= 2
        assert data["data"]["total"] == len(sample_expressions)

    async def test_get_expression_list_with_name_filter(self, client: AsyncClient, sample_expressions):
        """测试获取表情列表 - 名称过滤"""
        # 应该只返回包含"开心"的表情
        response = await client.get(f"{EXPRESSION_BASE_URL}?nameOrCode=开心")
        assert response.status_code == 200
        data = response.json()
        items = data["data"]["items"]
        assert len(items) == 1
        assert "开心" in items[0]["name"] or "开心" in items[0]["code"]

    async def test_get_expression_list_with_code_filter(self, client: AsyncClient, sample_expressions):
        """测试获取表情列表 - 代码过滤"""
        # 应该只返回包含"happy"的表情
        response = await client.get(f"{EXPRESSION_BASE_URL}?nameOrCode=happy")
        assert response.status_code == 200
        data = response.json()
        items = data["data"]["items"]
        assert len(items) == 1
        assert "happy" in items[0]["name"] or "happy" in items[0]["code"]

    async def test_get_expression_list_with_active_filter(self, client: AsyncClient, sample_expressions):
        """测试获取表情列表 - 启用状态过滤"""
        # 测试只获取启用的表情
        response = await client.get(f"{EXPRESSION_BASE_URL}?isActive=true")

        assert response.status_code == 200
        data = response.json()

        for item in data["data"]["items"]:
            assert item["isActive"] is True

        # 测试只获取禁用的表情
        response = await client.get(f"{EXPRESSION_BASE_URL}?isActive=false")

        assert response.status_code == 200
        data = response.json()

        for item in data["data"]["items"]:
            assert item["isActive"] is False

    async def test_get_expression_list_with_combined_filters(self, client: AsyncClient, sample_expressions):
        """测试获取表情列表 - 组合过滤条件"""
        response = await client.get(f"{EXPRESSION_BASE_URL}?nameOrCode=测试&isActive=true")

        assert response.status_code == 200
        data = response.json()

        for item in data["data"]["items"]:
            assert item["isActive"] is True
            assert "测试" in item["name"] or "测试" in item["code"]

    async def test_get_expression_detail_success(self, client: AsyncClient, sample_expressions):
        """测试获取表情详情 - 成功"""
        expression = sample_expressions[0].json()["data"]

        expression_id = expression.get("id")
        response = await client.get(f"{EXPRESSION_BASE_URL}/{expression_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["data"]["id"] == expression_id
        assert data["data"]["name"] == expression.get("name")
        assert data["data"]["code"] == expression.get("code")

    async def test_get_expression_detail_not_found(self, client: AsyncClient):
        """测试获取表情详情 - 不存在的ID"""
        response = await client.get("{EXPRESSION_BASE_URL}/99999")

        assert response.status_code == 404

    async def test_create_expression_success(self, client: AsyncClient):
        """测试创建表情 - 成功"""
        expression_data = {"name": "新表情", "code": "new_expr", "description": "这是一个新的表情", "isActive": True}

        response = await client.post(EXPRESSION_BASE_URL, json=expression_data)

        assert response.status_code == 200
        data = response.json()

        assert data["data"]["name"] == expression_data["name"]
        assert data["data"]["code"] == expression_data["code"]
        assert data["data"]["description"] == expression_data["description"]
        assert data["data"]["isActive"] == expression_data["isActive"]
        assert "id" in data["data"]

    async def test_create_expression_invalid_data(self, client: AsyncClient):
        """测试创建表情 - 无效数据"""
        # 测试缺少必填字段
        invalid_data = {"description": "缺少名称和代码"}

        response = await client.post(EXPRESSION_BASE_URL, json=invalid_data)

        assert response.status_code == 422

    async def test_create_expression_duplicate_code(self, client: AsyncClient, sample_expressions):
        """测试创建表情 - 重复代码"""
        expression = sample_expressions[0].json()["data"]
        expression_data = {
            "name": "重复代码表情",
            "code": expression.get("code"),  # 使用已存在的代码
            "description": "这个代码已经存在",
            "isActive": True,
        }

        response = await client.post(EXPRESSION_BASE_URL, json=expression_data)

        # 根据你的业务逻辑，这里可能返回 400 或其他错误码
        assert response.status_code == 409

    async def test_update_expression_success(self, client: AsyncClient, sample_expressions):
        """测试更新表情 - 成功"""
        expression = sample_expressions[0].json()["data"]
        expression_id = expression.get("id")
        update_data = {"name": "更新后的表情", "description": "更新后的描述", "isActive": False}

        response = await client.put(f"{EXPRESSION_BASE_URL}/{expression_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()

        assert data["data"]["id"] == expression_id
        assert data["data"]["name"] == update_data["name"]
        assert data["data"]["description"] == update_data["description"]
        assert data["data"]["isActive"] == update_data["isActive"]

    async def test_update_expression_partial(self, client: AsyncClient, sample_expressions):
        """测试更新表情 - 部分更新"""
        expression = sample_expressions[0].json()["data"]
        expression_id = expression.get("id")
        original_name = expression["name"]

        update_data = {"description": "只更新描述"}

        response = await client.put(f"{EXPRESSION_BASE_URL}/{expression_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()

        assert data["data"]["id"] == expression_id
        assert data["data"]["name"] == original_name  # 名称应该保持不变
        assert data["data"]["description"] == update_data["description"]

    async def test_update_expression_not_found(self, client: AsyncClient):
        """测试更新表情 - 不存在的ID"""
        update_data = {"name": "不存在的表情", "description": "这个ID不存在"}

        response = await client.put("{EXPRESSION_BASE_URL}/99999", json=update_data)

        assert response.status_code == 404

    async def test_update_expression_invalid_data(self, client: AsyncClient, sample_expressions):
        """测试更新表情 - 无效数据"""
        expression = sample_expressions[0].json()["data"]
        expression_id = expression.get("id")

        # 测试无效的数据类型
        invalid_data = {"isActive": "invalid_boolean"}

        response = await client.put(f"{EXPRESSION_BASE_URL}/{expression_id}", json=invalid_data)

        assert response.status_code == 422

    async def test_delete_expression_success(self, client: AsyncClient, sample_expressions):
        """测试删除表情 - 成功"""
        expression = sample_expressions[0].json()["data"]
        expression_id = expression.get("id")

        response = await client.delete(f"{EXPRESSION_BASE_URL}/{expression_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["msg"] == "删除成功"

        # 验证表情确实被删除了
        get_response = await client.get(f"{EXPRESSION_BASE_URL}/{expression_id}")
        assert get_response.status_code == 404

    async def test_delete_expression_not_found(self, client: AsyncClient):
        """测试删除表情 - 不存在的ID"""
        response = await client.delete("{EXPRESSION_BASE_URL}/99999")

        assert response.status_code == 404

    async def test_expression_list_ordering(self, client: AsyncClient, sample_expressions):
        """测试表情列表排序"""
        response = await client.get(EXPRESSION_BASE_URL)

        assert response.status_code == 200
        data = response.json()

        items = data["data"]["items"]

        # 验证按 ID 降序排列
        if len(items) > 1:
            for i in range(len(items) - 1):
                assert items[i]["id"] >= items[i + 1]["id"]

    async def test_expression_data_structure(self, client: AsyncClient, sample_expressions):
        """测试表情数据结构"""
        expression = sample_expressions[0].json()["data"]
        expression_id = expression.get("id")
        response = await client.get(f"{EXPRESSION_BASE_URL}/{expression_id}")

        assert response.status_code == 200
        data = response.json()

        expression_data = data["data"]

        # 验证必要字段存在
        required_fields = ["id", "name", "code", "description", "isActive", "createTime", "updateTime"]
        for field in required_fields:
            assert field in expression_data

        # 验证数据类型
        assert isinstance(expression_data["id"], int)
        assert isinstance(expression_data["name"], str)
        assert isinstance(expression_data["code"], str)
        assert isinstance(expression_data["isActive"], bool)

    async def test_expression_list_empty_result(self, client: AsyncClient):
        """测试表情列表 - 空结果"""
        # 使用不存在的过滤条件
        response = await client.get(f"{EXPRESSION_BASE_URL}?nameOrCode=不存在的表情")

        assert response.status_code == 200
        data = response.json()

        assert data["data"]["total"] == 0
        assert len(data["data"]["items"]) == 0

    async def test_expression_list_large_page_size(self, client: AsyncClient, sample_expressions):
        """测试表情列表 - 大页面大小"""
        response = await client.get(f"{EXPRESSION_BASE_URL}?size=100")

        assert response.status_code == 200
        data = response.json()

        assert data["data"]["size"] == 100
        assert len(data["data"]["items"]) <= data["data"]["total"]
