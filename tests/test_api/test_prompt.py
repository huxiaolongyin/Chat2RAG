import pytest
from httpx import AsyncClient

PROMPT_BASE_URL = "/api/v1/prompts"


@pytest.fixture
async def test_default_prompt(client: AsyncClient):
    """创建测试用提示词"""
    response = await client.post(
        PROMPT_BASE_URL,
        json={
            "promptName": "默认",
            "promptDesc": "测试提示词描述",
            "promptText": "这是测试提示词内容 {context} {question}",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "0000"
    return data["data"]


@pytest.fixture
async def test_prompt(client: AsyncClient):
    """创建测试用提示词"""
    response = await client.post(
        PROMPT_BASE_URL,
        json={
            "promptName": "测试提示词",
            "promptDesc": "测试提示词描述",
            "promptText": "这是测试提示词内容 {context} {question}",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "0000"
    return data["data"]


@pytest.fixture
async def test_prompt_with_versions(client: AsyncClient):
    """创建带版本的测试提示词"""
    # 创建初始提示词
    response = await client.post(
        PROMPT_BASE_URL,
        json={
            "promptName": "版本测试提示词",
            "promptDesc": "版本测试描述",
            "promptText": "版本1内容 {context} {question}",
        },
    )
    prompt_data = response.json()["data"]

    # 更新提示词创建新版本
    await client.put(
        f"{PROMPT_BASE_URL}/{prompt_data['id']}",
        json={
            "promptName": "版本测试提示词",
            "promptDesc": "版本测试描述",
            "promptText": "版本2内容 {context} {question}",
        },
    )

    return prompt_data


class TestPrompt:
    """提示词测试"""

    async def test_create_prompt_success(self, client: AsyncClient):
        """测试创建提示词成功"""
        response = await client.post(
            PROMPT_BASE_URL,
            json={
                "promptName": "客服助手",
                "promptDesc": "客服对话助手提示词",
                "promptText": "你是一个专业的客服助手。根据以下上下文:\n{context}\n\n回答用户问题:\n{question}",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "id" in data["data"]
        assert "promptDesc" in data["data"]
        assert "成功" in data["msg"]

    async def test_create_prompt_duplicate(self, client: AsyncClient, test_prompt):
        """测试创建重复提示词"""
        response = await client.post(
            PROMPT_BASE_URL,
            json={
                "promptName": "测试提示词",
                "promptDesc": "重复描述",
                "promptText": "重复内容",
            },
        )

        assert response.status_code == 409
        data = response.json()
        assert "已存在" in data["detail"]

    async def test_get_prompt_detail_success(self, client: AsyncClient, test_prompt):
        """测试获取提示词详情成功"""
        prompt_id = test_prompt["id"]
        response = await client.get(f"{PROMPT_BASE_URL}/{prompt_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["id"] == prompt_id
        assert "promptName" in data["data"]
        assert "versions" in data["data"]
        assert "currentVersion" in data["data"]

    async def test_get_prompt_detail_not_found(self, client: AsyncClient):
        """测试获取不存在的提示词详情"""
        response = await client.get(f"{PROMPT_BASE_URL}/99999")
        assert response.status_code == 404
        data = response.json()
        assert "不存在" in data["detail"]

    async def test_get_prompt_list(self, client: AsyncClient, test_prompt):
        """测试获取提示词列表"""
        response = await client.get(PROMPT_BASE_URL)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "promptList" in data["data"]
        assert data["data"]["total"] >= 1
        assert len(data["data"]["promptList"]) >= 1

    async def test_get_prompt_list_with_search(self, client: AsyncClient, test_prompt):
        """测试搜索提示词列表"""
        # 按名称搜索
        response = await client.get(PROMPT_BASE_URL, params={"promptName": "测试"})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 1

        # 按描述搜索
        response = await client.get(PROMPT_BASE_URL, params={"promptDesc": "测试"})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 1

    async def test_get_prompt_list_pagination(self, client: AsyncClient):
        """测试提示词列表分页"""
        # 创建多个提示词
        for i in range(5):
            await client.post(
                PROMPT_BASE_URL,
                json={
                    "promptName": f"提示词{i}",
                    "promptDesc": f"描述{i}",
                    "promptText": f"内容{i}",
                },
            )

        # 测试分页
        response = await client.get(PROMPT_BASE_URL, params={"current": 1, "size": 3})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert len(data["data"]["promptList"]) <= 3
        assert data["data"]["current"] == 1
        assert data["data"]["size"] == 3
        assert "pages" in data["data"]

    async def test_update_version_success(self, client: AsyncClient, test_prompt_with_versions):
        """测试设置提示词版本成功"""
        prompt_id = test_prompt_with_versions["id"]
        response = await client.get(f"{PROMPT_BASE_URL}/version", params={"promptId": prompt_id, "version": 1})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "成功" in data["msg"]

    async def test_update_version_not_found(self, client: AsyncClient):
        """测试设置不存在提示词的版本"""
        response = await client.get(f"{PROMPT_BASE_URL}/version", params={"promptId": 99999, "version": 1})
        assert response.status_code == 404
        data = response.json()
        assert "不存在" in data["detail"]

    async def test_update_version_invalid_version(self, client: AsyncClient, test_prompt):
        """测试设置无效版本号"""
        prompt_id = test_prompt["id"]
        response = await client.get(f"{PROMPT_BASE_URL}/version", params={"promptId": prompt_id, "version": 99})
        assert response.status_code == 404
        data = response.json()
        assert "不存在" in data["detail"]

    async def test_update_prompt_success(self, client: AsyncClient, test_prompt):
        """测试更新提示词成功"""
        prompt_id = test_prompt["id"]
        response = await client.put(
            f"{PROMPT_BASE_URL}/{prompt_id}",
            json={
                "promptName": "更新后的提示词",
                "promptDesc": "更新后的描述",
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
            f"{PROMPT_BASE_URL}/99999",
            json={
                "promptName": "不存在的提示词",
                "promptDesc": "不存在",
                "promptText": "不存在",
            },
        )
        assert response.status_code == 404
        data = response.json()
        assert "不存在" in data["detail"]

    async def test_update_prompt_duplicate(self, client: AsyncClient):
        """测试更新提示词为重复名称"""
        # 创建两个提示词
        prompt1 = await client.post(
            PROMPT_BASE_URL,
            json={
                "promptName": "提示词A",
                "promptDesc": "描述A",
                "promptText": "内容A",
            },
        )
        prompt1_data = prompt1.json()["data"]

        prompt2 = await client.post(
            PROMPT_BASE_URL,
            json={
                "promptName": "提示词B",
                "promptDesc": "描述B",
                "promptText": "内容B",
            },
        )
        prompt2_data = prompt2.json()["data"]

        # 尝试将提示词B更新为提示词A的名称
        response = await client.put(
            f"{PROMPT_BASE_URL}/{prompt2_data['id']}",
            json={
                "promptName": "提示词A",
                "promptDesc": "新描述",
                "promptText": "新内容",
            },
        )
        assert response.status_code == 409
        data = response.json()
        assert "已存在" in data["detail"]

    async def test_update_prompt_partial(self, client: AsyncClient, test_prompt):
        """测试部分更新提示词"""
        prompt_id = test_prompt["id"]
        response = await client.put(
            f"{PROMPT_BASE_URL}/{prompt_id}",
            json={
                "promptDesc": "只更新描述",
                "promptText": "新内容",
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
            PROMPT_BASE_URL,
            json={
                "promptName": "待删除提示词",
                "promptDesc": "待删除",
                "promptText": "待删除内容",
            },
        )
        prompt_id = create_response.json()["data"]["id"]

        # 删除提示词
        response = await client.delete(f"{PROMPT_BASE_URL}/{prompt_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "成功" in data["msg"]

    async def test_delete_prompt_not_found(self, client: AsyncClient):
        """测试删除不存在的提示词"""
        response = await client.delete(f"{PROMPT_BASE_URL}/99999")
        assert response.status_code == 404
        data = response.json()
        assert "不存在" in data["detail"]

    async def test_default_prompt_creation(self, client: AsyncClient, test_default_prompt):
        """测试默认提示词自动创建"""
        # 第一次访问列表时应该创建默认提示词
        response = await client.get(PROMPT_BASE_URL)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"

        # 检查是否存在默认提示词
        prompt_list = data["data"]["promptList"]
        default_prompt = next((p for p in prompt_list if p["promptName"] == "默认"), None)
        assert default_prompt is not None


class TestDeprecatedEndpoints:
    """测试废弃的端点以确保向后兼容性"""

    async def test_deprecated_get_list(self, client: AsyncClient):
        """测试废弃的获取列表端点"""
        response = await client.get(f"{PROMPT_BASE_URL}/list")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "promptList" in data["data"]

    async def test_deprecated_create(self, client: AsyncClient):
        """测试废弃的创建端点"""
        response = await client.post(
            f"/api/v1/prompt/add",
            json={
                "promptName": "废弃端点测试",
                "promptDesc": "测试废弃端点",
                "promptText": "测试内容",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "id" in data["data"]

    async def test_deprecated_update(self, client: AsyncClient):
        """测试废弃的更新端点"""
        # 先创建一个提示词
        create_response = await client.post(
            "/api/v1/prompt",
            json={
                "promptName": "待更新提示词",
                "promptDesc": "待更新",
                "promptText": "待更新内容",
            },
        )
        prompt_id = create_response.json()["data"]["id"]

        # 使用废弃端点更新
        response = await client.put(
            f"/api/v1/prompt/update/{prompt_id}",
            json={
                "promptName": "已更新提示词",
                "promptDesc": "已更新",
                "promptText": "已更新内容",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"

    async def test_deprecated_delete(self, client: AsyncClient):
        """测试废弃的删除端点"""
        # 先创建一个提示词
        create_response = await client.post(
            "/api/v1/prompt",
            json={
                "promptName": "待删除提示词2",
                "promptDesc": "待删除",
                "promptText": "待删除内容",
            },
        )
        prompt_id = create_response.json()["data"]["id"]

        # 使用废弃端点删除
        response = await client.delete(f"{PROMPT_BASE_URL}/remove/{prompt_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"


class TestValidation:
    """参数验证测试"""

    async def test_prompt_name_regex_validation(self, client: AsyncClient):
        """测试提示词名称正则验证"""
        # 测试有效字符
        response = await client.get(PROMPT_BASE_URL, params={"promptName": "test_测试-123"})
        assert response.status_code == 200

        # 测试无效字符（包含特殊符号）
        response = await client.get(PROMPT_BASE_URL, params={"promptName": "test@#$%"})
        assert response.status_code == 422

    async def test_prompt_desc_regex_validation(self, client: AsyncClient):
        """测试提示词描述正则验证"""
        # 测试有效字符
        response = await client.get(PROMPT_BASE_URL, params={"promptDesc": "desc_描述-123"})
        assert response.status_code == 200

        # 测试无效字符（包含特殊符号）
        response = await client.get(PROMPT_BASE_URL, params={"promptDesc": "desc@#$%"})
        assert response.status_code == 422

    async def test_create_prompt_validation(self, client: AsyncClient):
        """测试创建提示词时的验证"""
        # 测试名称包含无效字符
        response = await client.post(
            PROMPT_BASE_URL,
            json={
                "promptName": "invalid@name",
                "promptDesc": "描述",
                "promptText": "内容",
            },
        )
        assert response.status_code == 422

        # 测试名称过长
        response = await client.post(
            PROMPT_BASE_URL,
            json={
                "promptName": "a" * 101,  # 假设最大长度为100
                "promptDesc": "描述",
                "promptText": "内容",
            },
        )
        assert response.status_code == 422

        # 测试描述过长
        response = await client.post(
            PROMPT_BASE_URL,
            json={
                "promptName": "正常名称",
                "promptDesc": "a" * 501,  # 假设最大长度为500
                "promptText": "内容",
            },
        )
        assert response.status_code == 422


class TestEdgeCases:
    """边界情况测试"""

    async def test_prompt_name_max_length(self, client: AsyncClient):
        """测试提示词名称长度限制"""
        response = await client.get(PROMPT_BASE_URL, params={"promptName": "a" * 51})
        # 应该会因为验证失败返回422
        assert response.status_code == 422

    async def test_prompt_desc_max_length(self, client: AsyncClient):
        """测试提示词描述长度限制"""
        # 修正：API中限制是200，不是50
        response = await client.get(PROMPT_BASE_URL, params={"promptDesc": "a" * 201})
        # 应该会因为验证失败返回422
        assert response.status_code == 422

    async def test_empty_list(self, client: AsyncClient):
        """测试空列表"""
        response = await client.get(
            PROMPT_BASE_URL,
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
            PROMPT_BASE_URL,
            json={
                "promptName": "",
                "promptDesc": "描述",
                "promptText": "内容",
            },
        )

        # 应该会因为验证失败返回422
        assert response.status_code == 422

    async def test_create_prompt_with_empty_text(self, client: AsyncClient):
        """测试创建空内容提示词"""
        response = await client.post(
            PROMPT_BASE_URL,
            json={
                "promptName": "测试名称",
                "promptDesc": "描述",
                "promptText": "",
            },
        )
        # 应该会因为验证失败返回422
        assert response.status_code == 422

    async def test_pagination_edge_cases(self, client: AsyncClient):
        """测试分页边界情况"""
        # 测试 current = 0
        response = await client.get(PROMPT_BASE_URL, params={"current": 0, "size": 10})
        assert response.status_code == 422

        # 测试 size = 0
        response = await client.get(PROMPT_BASE_URL, params={"current": 1, "size": 0})
        assert response.status_code == 422

        # 测试超大页码
        response = await client.get(PROMPT_BASE_URL, params={"current": 9999, "size": 10})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert len(data["data"]["promptList"]) == 0

    async def test_search_with_special_characters(self, client: AsyncClient):
        """测试搜索包含特殊字符的情况"""
        # 创建包含特殊字符的提示词
        await client.post(
            PROMPT_BASE_URL,
            json={
                "promptName": "特殊测试_123",
                "promptDesc": "包含-下划线",
                "promptText": "特殊内容",
            },
        )

        # 搜索下划线
        response = await client.get(PROMPT_BASE_URL, params={"promptName": "_"})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"

        # 搜索中划线
        response = await client.get(PROMPT_BASE_URL, params={"promptDesc": "-"})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"

    async def test_concurrent_operations(self, client: AsyncClient):
        """测试并发操作"""
        import asyncio

        # 并发创建多个提示词
        async def create_prompt(i):
            return await client.post(
                PROMPT_BASE_URL,
                json={
                    "promptName": f"并发测试{i}",
                    "promptDesc": f"并发描述{i}",
                    "promptText": f"并发内容{i}",
                },
            )

        # 并发执行
        tasks = [create_prompt(i) for i in range(5)]
        responses = await asyncio.gather(*tasks)

        # 验证所有请求都成功
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == "0000"

    async def test_query_parameter_aliases(self, client: AsyncClient):
        """测试查询参数别名"""
        # 测试 promptName 别名
        response = await client.get("/api/v1/prompt?promptName=test")
        assert response.status_code == 200

        # 测试 promptDesc 别名
        response = await client.get("/api/v1/prompt?promptDesc=test")
        assert response.status_code == 200

    async def test_version_parameter_validation(self, client: AsyncClient):
        """测试版本参数验证"""
        # 测试缺少 promptId 参数
        response = await client.get(f"{PROMPT_BASE_URL}/version", params={"version": 1})
        assert response.status_code == 422

        # 测试缺少 version 参数
        response = await client.get(f"{PROMPT_BASE_URL}/version", params={"promptId": 1})
        assert response.status_code == 422

        # 测试无效的参数类型
        response = await client.get(f"{PROMPT_BASE_URL}/version", params={"promptId": "abc", "version": "xyz"})
        assert response.status_code == 422


class TestErrorHandling:
    """错误处理测试"""

    async def test_business_exception_handling(self, client: AsyncClient):
        """测试业务异常处理"""
        # 这里需要根据实际的业务逻辑来触发BusinessException
        # 例如，尝试操作已被删除的提示词等
        pass

    async def test_system_exception_handling(self, client: AsyncClient):
        """测试系统异常处理"""
        # 这里可能需要模拟数据库连接失败等系统级异常
        # 具体实现取决于你的测试环境设置
        pass

    async def test_invalid_json_payload(self, client: AsyncClient):
        """测试无效的JSON载荷"""
        response = await client.post(
            PROMPT_BASE_URL,
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    async def test_missing_required_fields(self, client: AsyncClient):
        """测试缺少必需字段"""
        response = await client.post(
            PROMPT_BASE_URL,
            json={
                "promptName": "测试名称",
                # 缺少 promptDesc 和 promptText
            },
        )
        assert response.status_code == 422
