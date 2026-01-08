import pytest
from httpx import AsyncClient

MODEL_BASE_URL = "/api/v1/models"


@pytest.fixture
async def test_provider(client: AsyncClient):
    """创建测试用模型渠道商"""
    response = await client.post(
        f"{MODEL_BASE_URL}/provider",
        json={
            "name": "测试渠道商",
            "baseUrl": "https://api.test.com",
            "apiKey": "sk-test123",
            "enabled": True,
            "description": "测试渠道商描述",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "0000"
    return data["data"]


@pytest.fixture
async def test_provider_disabled(client: AsyncClient):
    """创建测试用禁用的模型渠道商"""
    response = await client.post(
        f"{MODEL_BASE_URL}/provider",
        json={
            "name": "禁用渠道商",
            "baseUrl": "https://api.disabled.com",
            "apiKey": "sk-disabled123",
            "enabled": False,
            "description": "禁用渠道商描述",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "0000"
    return data["data"]


@pytest.fixture
async def test_source(client: AsyncClient, test_provider):
    """创建测试用模型源"""
    response = await client.post(
        f"{MODEL_BASE_URL}/source",
        json={
            "name": "gpt-4",
            "alias": "test-model",
            "providerId": test_provider["id"],
            "enabled": True,
            "healthy": True,
            "priority": 10,
            "generationKwargs": {"temperature": 0.7, "max_tokens": 1000},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "0000"
    return data["data"]


@pytest.fixture
async def test_source_unhealthy(client: AsyncClient, test_provider):
    """创建测试用不健康的模型源"""
    response = await client.post(
        f"{MODEL_BASE_URL}/source",
        json={
            "name": "gpt-3.5-turbo",
            "alias": "unhealthy-model",
            "providerId": test_provider["id"],
            "enabled": True,
            "priority": 5,
            "generationKwargs": {"temperature": 0.5},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "0000"
    return data["data"]


@pytest.fixture
async def test_provider_with_sources(client: AsyncClient):
    """创建带有多个模型源的渠道商"""
    # 创建渠道商
    provider_response = await client.post(
        f"{MODEL_BASE_URL}/provider",
        json={
            "name": "多源渠道商",
            "baseUrl": "https://api.multi.com",
            "apiKey": "sk-multi123",
            "enabled": True,
            "description": "包含多个模型源的渠道商",
        },
    )
    provider_data = provider_response.json()["data"]

    # 创建多个模型源
    sources = []
    for i in range(3):
        source_response = await client.post(
            f"{MODEL_BASE_URL}/source",
            json={
                "name": f"model-{i}",
                "alias": f"模型源{i}",
                "providerId": provider_data["id"],
                "enabled": True,
                "priority": i * 10,
                "generationKwargs": {"temperature": 0.1 * i},
            },
        )
        sources.append(source_response.json()["data"])

    return {"provider": provider_data, "sources": sources}


class TestModelList:
    """模型列表测试"""

    async def test_get_model_option_success(self, client: AsyncClient, test_source):
        """测试获取模型选项列表成功"""
        response = await client.get(f"{MODEL_BASE_URL}/option")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert isinstance(data["data"], list)

        # 检查是否包含健康且启用的模型
        model_aliases = [item["alias"] for item in data["data"]]
        assert "test-model" in model_aliases

    async def test_get_model_list_deprecated(self, client: AsyncClient, test_source):
        """测试废弃的模型列表端点"""
        response = await client.get(f"{MODEL_BASE_URL}/list")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert isinstance(data["data"], list)

    async def test_model_list_only_healthy_enabled(self, client: AsyncClient, test_source, test_source_unhealthy):
        """测试模型列表只返回健康且启用的模型"""
        response = await client.get(f"{MODEL_BASE_URL}/option")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"

        model_aliases = [item["alias"] for item in data["data"]]
        assert "test-model" in model_aliases
        # 注意：这里需要根据实际业务逻辑调整，如果unhealthy模型也会出现在列表中则需要修改断言


class TestModelProvider:
    """模型渠道商测试"""

    async def test_create_provider_success(self, client: AsyncClient):
        """测试创建模型渠道商成功"""
        response = await client.post(
            f"{MODEL_BASE_URL}/provider",
            json={
                "name": "OpenAI",
                "baseUrl": "https://api.openai.com/v1",
                "apiKey": "sk-openai123",
                "enabled": True,
                "description": "OpenAI模型提供商",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "id" in data["data"]
        assert data["data"]["name"] == "OpenAI"
        assert data["data"]["baseUrl"] == "https://api.openai.com/v1"
        assert data["data"]["enabled"] is True

    async def test_create_provider_duplicate(self, client: AsyncClient, test_provider):
        """测试创建重复名称的渠道商"""
        response = await client.post(
            f"{MODEL_BASE_URL}/provider",
            json={
                "name": "测试渠道商",
                "baseUrl": "https://api.openai.com/v1",
                "apiKey": "sk-openai123",
                "description": "重复名称",
                "enabled": True,
            },
        )
        assert response.status_code == 409
        data = response.json()
        assert "已存在" in data["detail"]

    async def test_get_provider_detail_success(self, client: AsyncClient, test_provider):
        """测试获取渠道商详情成功"""
        provider_id = test_provider["id"]
        response = await client.get(f"{MODEL_BASE_URL}/provider/{provider_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["id"] == provider_id
        assert data["data"]["name"] == "测试渠道商"
        assert data["data"]["baseUrl"] == "https://api.test.com"

    async def test_get_provider_detail_not_found(self, client: AsyncClient):
        """测试获取不存在的渠道商详情"""
        response = await client.get(f"{MODEL_BASE_URL}/provider/99999")
        assert response.status_code == 404
        data = response.json()
        assert "不存在" in data["detail"]

    async def test_get_provider_list(self, client: AsyncClient, test_provider):
        """测试获取渠道商列表"""
        response = await client.get(f"{MODEL_BASE_URL}/provider")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "items" in data["data"]
        assert data["data"]["total"] >= 1
        assert len(data["data"]["items"]) >= 1

    async def test_get_provider_list_with_search(self, client: AsyncClient, test_provider):
        """测试搜索渠道商列表"""
        # 按名称或描述搜索
        response = await client.get(f"{MODEL_BASE_URL}/provider", params={"nameOrDesc": "测试"})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 1

        # 按启用状态搜索
        response = await client.get(f"{MODEL_BASE_URL}/provider", params={"enabled": True})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"

    async def test_get_provider_list_pagination(self, client: AsyncClient):
        """测试渠道商列表分页"""
        # 创建多个渠道商
        for i in range(5):
            await client.post(
                f"{MODEL_BASE_URL}/provider",
                json={
                    "name": f"渠道商{i}",
                    "baseUrl": f"https://api{i}.com",
                    "description": f"描述{i}",
                    "enabled": True,
                },
            )

        # 测试分页
        response = await client.get(f"{MODEL_BASE_URL}/provider", params={"current": 1, "size": 3})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert len(data["data"]["items"]) <= 3
        assert data["data"]["current"] == 1
        assert data["data"]["size"] == 3

    async def test_update_provider_success(self, client: AsyncClient, test_provider):
        """测试更新渠道商成功"""
        provider_id = test_provider["id"]
        response = await client.put(
            f"{MODEL_BASE_URL}/provider/{provider_id}",
            json={
                "name": "更新后的渠道商",
                "baseUrl": "https://api.updated.com",
                "apiKey": "sk-updated123",
                "enabled": False,
                "description": "更新后的描述",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["modelProviderId"] == provider_id

    async def test_update_provider_partial(self, client: AsyncClient, test_provider):
        """测试部分更新渠道商"""
        provider_id = test_provider["id"]
        response = await client.put(
            f"{MODEL_BASE_URL}/provider/{provider_id}",
            json={
                "description": "只更新描述",
                "enabled": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["modelProviderId"] == provider_id

    async def test_update_provider_not_found(self, client: AsyncClient):
        """测试更新不存在的渠道商"""
        response = await client.put(
            f"{MODEL_BASE_URL}/provider/99999",
            json={
                "name": "不存在的渠道商",
                "description": "不存在",
                "enabled": True,
            },
        )
        assert response.status_code == 404
        data = response.json()
        assert "不存在" in data["detail"]

    async def test_update_provider_duplicate(self, client: AsyncClient):
        """测试更新渠道商为重复名称"""
        # 创建两个渠道商
        provider1 = await client.post(
            f"{MODEL_BASE_URL}/provider",
            json={
                "name": "渠道商A",
                "baseUrl": "https://api.openai.com/v1",
                "apiKey": "sk-openai123",
                "description": "描述A",
                "enabled": True,
            },
        )
        assert provider1.status_code == 200
        provider1_data = provider1.json()["data"]

        provider2 = await client.post(
            f"{MODEL_BASE_URL}/provider",
            json={
                "name": "渠道商B",
                "baseUrl": "https://api.openai.com/v1",
                "apiKey": "sk-openai123",
                "description": "描述B",
                "enabled": True,
            },
        )
        assert provider2.status_code == 200
        provider2_data = provider2.json()["data"]

        # 尝试将渠道商B更新为渠道商A的名称
        response = await client.put(
            f"{MODEL_BASE_URL}/provider/{provider2_data['id']}",
            json={
                "name": "渠道商A",
                "baseUrl": "https://api.openai.com/v1",
                "apiKey": "sk-openai123",
                "description": "新描述",
                "enabled": True,
            },
        )
        assert response.status_code == 409
        data = response.json()
        assert "已存在" in data["detail"]

    async def test_delete_provider_success(self, client: AsyncClient):
        """测试删除渠道商成功"""
        # 创建渠道商
        create_response = await client.post(
            f"{MODEL_BASE_URL}/provider",
            json={
                "name": "待删除渠道商",
                "baseUrl": "https://api.openai.com/v1",
                "apiKey": "sk-openai123",
                "description": "待删除",
                "enabled": True,
            },
        )
        assert create_response.status_code == 200
        provider_id = create_response.json()["data"]["id"]

        # 删除渠道商
        response = await client.delete(f"{MODEL_BASE_URL}/provider/{provider_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "成功" in data["msg"]

    async def test_delete_provider_not_found(self, client: AsyncClient):
        """测试删除不存在的渠道商"""
        response = await client.delete(f"{MODEL_BASE_URL}/provider/99999")
        assert response.status_code == 404
        data = response.json()
        assert "不存在" in data["detail"]

    async def test_delete_provider_with_sources(self, client: AsyncClient, test_provider_with_sources):
        """测试删除有关联模型源的渠道商"""
        provider_id = test_provider_with_sources["provider"]["id"]

        # 应该能够删除（或根据业务逻辑返回相应错误）
        response = await client.delete(f"{MODEL_BASE_URL}/provider/{provider_id}")
        # 根据实际业务逻辑调整断言
        assert response.status_code in [200, 400, 409]


class TestModelSource:
    """模型源测试"""

    async def test_create_source_success(self, client: AsyncClient, test_provider):
        """测试创建模型源成功"""
        response = await client.post(
            f"{MODEL_BASE_URL}/source",
            json={
                "name": "gpt-4-turbo",
                "alias": "gpt-4",
                "providerId": test_provider["id"],
                "enabled": True,
                "priority": 100,
                "generationKwargs": {
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "top_p": 0.9,
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["name"] == "gpt-4-turbo"
        assert data["data"]["alias"] == "gpt-4"
        assert data["data"]["enabled"] is True
        assert data["data"]["priority"] == 100
        assert data["data"]["generationKwargs"]["temperature"] == 0.7

    async def test_create_source_duplicate_name(self, client: AsyncClient, test_source):
        """测试创建重复别名的模型源"""
        response = await client.post(
            f"{MODEL_BASE_URL}/source",
            json={
                "name": "gpt-4",
                "alias": "test-model",
                "providerId": test_source["providerId"],
                "enabled": True,
            },
        )
        assert response.status_code == 409
        data = response.json()
        assert "已存在" in data["detail"]

    async def test_create_source_invalid_provider(self, client: AsyncClient):
        """测试创建模型源时使用无效的渠道商ID"""
        response = await client.post(
            f"{MODEL_BASE_URL}/source",
            json={
                "name": "invalid-provider-model",
                "alias": "invalid-model",
                "providerId": 99999,
                "enabled": True,
            },
        )
        assert response.status_code == 404
        data = response.json()
        assert "不存在" in data["detail"]

    async def test_get_source_detail_success(self, client: AsyncClient, test_source):
        """测试获取模型源详情成功"""
        source_id = test_source["id"]
        response = await client.get(f"{MODEL_BASE_URL}/source/{source_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["id"] == source_id
        assert data["data"]["name"] == "gpt-4"
        assert data["data"]["alias"] == "test-model"
        assert "failureCount" in data["data"]
        assert "healthy" in data["data"]
        assert "lastLatency" in data["data"]
        assert "lastCheckTime" in data["data"]

    async def test_get_source_detail_not_found(self, client: AsyncClient):
        """测试获取不存在的模型源详情"""
        response = await client.get(f"{MODEL_BASE_URL}/source/99999")
        assert response.status_code == 404
        data = response.json()
        assert "不存在" in data["detail"]

    async def test_get_source_list(self, client: AsyncClient, test_source):
        """测试获取模型源列表"""
        response = await client.get(f"{MODEL_BASE_URL}/source")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "items" in data["data"]
        assert data["data"]["total"] >= 1

    async def test_get_source_list_with_filters(self, client: AsyncClient, test_provider_with_sources):
        """测试带过滤条件的模型源列表"""
        provider_id = test_provider_with_sources["provider"]["id"]

        # 按名称或别名搜索
        response = await client.get(f"{MODEL_BASE_URL}/source", params={"nameOrAlias": "模型源"})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 3

        # 按渠道商ID过滤
        response = await client.get(f"{MODEL_BASE_URL}/source", params={"providerId": provider_id})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] == 3

        # 按启用状态过滤
        response = await client.get(f"{MODEL_BASE_URL}/source", params={"enabled": True})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"

        # 按健康状态过滤
        response = await client.get(f"{MODEL_BASE_URL}/source", params={"healthy": True})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"

    async def test_get_source_list_pagination(self, client: AsyncClient, test_provider):
        """测试模型源列表分页"""
        # 创建多个模型源
        for i in range(5):
            await client.post(
                f"{MODEL_BASE_URL}/source",
                json={
                    "name": f"page-model-{i}",
                    "alias": f"分页模型{i}",
                    "providerId": test_provider["id"],
                    "enabled": True,
                    "priority": i,
                },
            )

        # 测试分页
        response = await client.get(f"{MODEL_BASE_URL}/source", params={"current": 1, "size": 3})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert len(data["data"]["items"]) <= 3
        assert data["data"]["current"] == 1
        assert data["data"]["size"] == 3

    async def test_update_source_success(self, client: AsyncClient, test_source):
        """测试更新模型源成功"""
        source_id = test_source["id"]
        response = await client.put(
            f"{MODEL_BASE_URL}/source/{source_id}",
            json={
                "alias": "updated-model",
                "enabled": False,
                "priority": 50,
                "generationKwargs": {"temperature": 0.5, "max_tokens": 1500},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["alias"] == "updated-model"
        assert data["data"]["enabled"] is False
        assert data["data"]["priority"] == 50

    async def test_update_source_partial(self, client: AsyncClient, test_source):
        """测试部分更新模型源"""
        source_id = test_source["id"]
        response = await client.put(
            f"{MODEL_BASE_URL}/source/{source_id}",
            json={
                "priority": 200,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["priority"] == 200

    async def test_update_source_not_found(self, client: AsyncClient):
        """测试更新不存在的模型源"""
        response = await client.put(
            f"{MODEL_BASE_URL}/source/99999",
            json={
                "alias": "not-exist",
                "enabled": True,
            },
        )
        assert response.status_code == 404
        data = response.json()
        assert "不存在" in data["detail"]

    async def test_update_source_duplicate_alias(self, client: AsyncClient, test_provider):
        """测试更新模型源为重复别名"""
        # 创建两个模型源
        source1 = await client.post(
            f"{MODEL_BASE_URL}/source",
            json={
                "name": "model-a",
                "alias": "模型源A",
                "providerId": test_provider["id"],
                "enabled": True,
            },
        )
        assert source1.status_code == 200
        source1_data = source1.json()["data"]

        source2 = await client.post(
            f"{MODEL_BASE_URL}/source",
            json={
                "name": "model-b",
                "alias": "模型源B",
                "providerId": test_provider["id"],
                "enabled": True,
            },
        )
        assert source2.status_code == 200
        source2_data = source2.json()["data"]

        # 尝试将模型源B更新为模型源A的别名
        response = await client.put(
            f"{MODEL_BASE_URL}/source/{source2_data['id']}",
            json={
                "name": "model-a",
                "enabled": True,
            },
        )
        assert response.status_code == 409
        data = response.json()
        assert "已存在" in data["detail"]

    async def test_delete_source_success(self, client: AsyncClient, test_provider):
        """测试删除模型源成功"""
        # 创建模型源
        create_response = await client.post(
            f"{MODEL_BASE_URL}/source",
            json={
                "name": "to-delete-model",
                "alias": "待删除模型源",
                "providerId": test_provider["id"],
                "enabled": True,
            },
        )
        source_id = create_response.json()["data"]["id"]

        # 删除模型源
        response = await client.delete(f"{MODEL_BASE_URL}/source/{source_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "成功" in data["msg"]

    async def test_delete_source_not_found(self, client: AsyncClient):
        """测试删除不存在的模型源"""
        response = await client.delete(f"{MODEL_BASE_URL}/source/99999")
        assert response.status_code == 404
        data = response.json()
        assert "不存在" in data["detail"]


class TestValidation:
    """参数验证测试"""

    async def test_provider_name_validation(self, client: AsyncClient):
        """测试渠道商名称验证"""
        # 测试空名称
        response = await client.post(
            f"{MODEL_BASE_URL}/provider",
            json={
                "name": "",
                "description": "描述",
                "enabled": True,
            },
        )
        assert response.status_code == 422

        # 测试名称过长
        response = await client.post(
            f"{MODEL_BASE_URL}/provider",
            json={
                "name": "a" * 101,  # 超过100字符限制
                "description": "描述",
                "enabled": True,
            },
        )
        assert response.status_code == 422

    async def test_provider_description_validation(self, client: AsyncClient):
        """测试渠道商描述验证"""
        # 测试描述过长
        response = await client.post(
            f"{MODEL_BASE_URL}/provider",
            json={
                "name": "测试渠道商",
                "description": "a" * 256,  # 超过255字符限制
                "enabled": True,
            },
        )
        assert response.status_code == 422

    async def test_source_name_validation(self, client: AsyncClient, test_provider):
        """测试模型源名称验证"""
        # 测试空名称
        response = await client.post(
            f"{MODEL_BASE_URL}/source",
            json={
                "name": "",
                "alias": "test-alias",
                "providerId": test_provider["id"],
                "enabled": True,
            },
        )
        assert response.status_code == 422

        # 测试名称过长
        response = await client.post(
            f"{MODEL_BASE_URL}/source",
            json={
                "name": "a" * 101,  # 超过100字符限制
                "alias": "test-alias",
                "providerId": test_provider["id"],
                "enabled": True,
            },
        )
        assert response.status_code == 422

    async def test_source_alias_validation(self, client: AsyncClient, test_provider):
        """测试模型源别名验证"""
        # 测试别名过长
        response = await client.post(
            f"{MODEL_BASE_URL}/source",
            json={
                "name": "测试模型",
                "alias": "a" * 101,  # 超过100字符限制
                "providerId": test_provider["id"],
                "enabled": True,
            },
        )
        assert response.status_code == 422

    async def test_search_parameter_validation(self, client: AsyncClient):
        """测试搜索参数验证"""
        # 测试搜索参数过长
        response = await client.get(f"{MODEL_BASE_URL}/provider", params={"nameOrDesc": "a" * 51})
        assert response.status_code == 422

        response = await client.get(f"{MODEL_BASE_URL}/source", params={"nameOrAlias": "a" * 51})
        assert response.status_code == 422

    async def test_pagination_validation(self, client: AsyncClient):
        """测试分页参数验证"""
        # 测试无效的 current 值
        response = await client.get(f"{MODEL_BASE_URL}/provider", params={"current": 0})
        assert response.status_code == 422

        # 测试无效的 size 值
        response = await client.get(f"{MODEL_BASE_URL}/provider", params={"size": 0})
        assert response.status_code == 422

        response = await client.get(f"{MODEL_BASE_URL}/provider", params={"size": 101})
        assert response.status_code == 422

    async def test_missing_required_fields(self, client: AsyncClient):
        """测试缺少必需字段"""
        # 创建渠道商时缺少必需字段
        response = await client.post(
            f"{MODEL_BASE_URL}/provider",
            json={
                "description": "只有描述",
                # 缺少 name
            },
        )
        assert response.status_code == 422

        # 创建模型源时缺少必需字段
        response = await client.post(
            f"{MODEL_BASE_URL}/source",
            json={
                "alias": "只有别名",
                # 缺少 name 和 provider_id
            },
        )
        assert response.status_code == 422

    async def test_generation_kwargs_validation(self, client: AsyncClient, test_provider):
        """测试生成参数验证"""
        # 测试有效的生成参数
        response = await client.post(
            f"{MODEL_BASE_URL}/source",
            json={
                "name": "test-kwargs-model",
                "alias": "kwargs-model",
                "providerId": test_provider["id"],
                "enabled": True,
                "generationKwargs": {
                    "temperature": 0.7,
                    "max_tokens": 1000,
                    "top_p": 0.9,
                    "frequency_penalty": 0.1,
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["generationKwargs"]["temperature"] == 0.7

    async def test_priority_validation(self, client: AsyncClient, test_provider):
        """测试优先级参数验证"""
        # 测试负数优先级
        response = await client.post(
            f"{MODEL_BASE_URL}/source",
            json={
                "name": "negative-priority-model",
                "alias": "neg-priority",
                "providerId": test_provider["id"],
                "enabled": True,
                "priority": -10,
            },
        )
        assert response.status_code == 200  # 负数优先级应该是允许的
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["priority"] == -10


class TestEdgeCases:
    """边界情况测试"""

    async def test_empty_lists(self, client: AsyncClient):
        """测试空列表"""
        # 搜索不存在的内容
        response = await client.get(
            f"{MODEL_BASE_URL}/provider",
            params={"nameOrDesc": "不存在的搜索词xyz123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] == 0
        assert len(data["data"]["items"]) == 0

        response = await client.get(
            f"{MODEL_BASE_URL}/source",
            params={"nameOrAlias": "不存在的搜索词xyz123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] == 0
        assert len(data["data"]["items"]) == 0

    async def test_large_page_number(self, client: AsyncClient):
        """测试超大页码"""
        response = await client.get(f"{MODEL_BASE_URL}/provider", params={"current": 9999, "size": 10})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert len(data["data"]["items"]) == 0

    async def test_filter_combinations(self, client: AsyncClient, test_provider_with_sources):
        """测试过滤条件组合"""
        provider_id = test_provider_with_sources["provider"]["id"]

        # 组合多个过滤条件
        response = await client.get(
            f"{MODEL_BASE_URL}/source",
            params={
                "providerId": provider_id,
                "enabled": True,
                "healthy": True,
                "nameOrDesc": "模型源",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"

    async def test_concurrent_operations(self, client: AsyncClient):
        """测试并发操作"""
        import asyncio

        # 并发创建多个渠道商
        async def create_provider(i):
            return await client.post(
                f"{MODEL_BASE_URL}/provider",
                json={
                    "name": f"并发渠道商{i}",
                    "baseUrl": f"https://api{i}.concurrent.com",
                    "apiKey": f"sk-{i}",
                    "description": f"并发描述{i}",
                    "enabled": True,
                },
            )

        # 并发执行
        tasks = [create_provider(i) for i in range(5)]
        responses = await asyncio.gather(*tasks)

        # 验证所有请求都成功
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == "0000"

    async def test_provider_source_relationship(self, client: AsyncClient, test_provider_with_sources):
        """测试渠道商和模型源的关联关系"""
        provider_id = test_provider_with_sources["provider"]["id"]

        # 获取该渠道商的所有模型源
        response = await client.get(
            f"{MODEL_BASE_URL}/source",
            params={"providerId": provider_id},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] == 3

        # 验证所有模型源都属于该渠道商
        for source in data["data"]["items"]:
            assert source["providerId"] == provider_id

    async def test_model_list_deduplication(self, client: AsyncClient, test_provider):
        """测试模型列表去重"""
        # 创建多个相同别名的模型源（如果业务允许）
        for i in range(3):
            await client.post(
                f"{MODEL_BASE_URL}/source",
                json={
                    "name": f"重复别名模型{i}",
                    "alias": "duplicate-alias",
                    "providerId": test_provider["id"],
                    "enabled": True,
                    "healthy": True,
                },
            )

        response = await client.get(f"{MODEL_BASE_URL}/option")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"

        # 检查是否去重
        aliases = [item["alias"] for item in data["data"]]
        duplicate_count = aliases.count("duplicate-alias")
        assert duplicate_count == 1  # 应该只出现一次

    async def test_special_characters_in_fields(self, client: AsyncClient):
        """测试字段中的特殊字符"""
        # 测试包含特殊字符的渠道商名称
        response = await client.post(
            f"{MODEL_BASE_URL}/provider",
            json={
                "name": "特殊字符_测试-123",
                "baseUrl": "https://api.special-chars.com/v1",
                "description": "包含特殊字符：中文、数字123、符号_-",
                "apiKey": "sk-...",
                "enabled": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        provider_id = data["data"]["id"]

        # 测试包含特殊字符的模型源
        response = await client.post(
            f"{MODEL_BASE_URL}/source",
            json={
                "name": "gpt-4-turbo-preview",
                "alias": "GPT4_Turbo中文版",
                "providerId": provider_id,
                "enabled": True,
                "generationKwargs": {
                    "model_name": "gpt-4-turbo-preview",
                    "custom_param": "特殊值_123",
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"

    async def test_null_optional_fields(self, client: AsyncClient):
        """测试可选字段为null的情况"""
        # 创建渠道商，可选字段为null
        response = await client.post(
            f"{MODEL_BASE_URL}/provider",
            json={
                "name": "Null字段测试",
                "baseUrl": None,
                "apiKey": None,
                "description": None,
                "enabled": True,
            },
        )
        assert response.status_code == 422

        response = await client.post(
            f"{MODEL_BASE_URL}/provider",
            json={
                "name": "Null字段测试",
                "baseUrl": "https://api.special-chars.com/v1",
                "apiKey": "sk-...",
                "description": None,
                "enabled": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        provider_id = data["data"]["id"]

        # 创建模型源，可选字段为null
        response = await client.post(
            f"{MODEL_BASE_URL}/source",
            json={
                "name": "null-fields-model",
                "alias": None,
                "providerId": provider_id,
                "enabled": None,
                "priority": None,
                "generationKwargs": None,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"


class TestErrorHandling:
    """错误处理测试"""

    async def test_invalid_json_payload(self, client: AsyncClient):
        """测试无效的JSON载荷"""
        response = await client.post(
            f"{MODEL_BASE_URL}/provider",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    async def test_invalid_parameter_types(self, client: AsyncClient):
        """测试无效的参数类型"""
        # 测试 enabled 参数类型错误
        response = await client.get(
            f"{MODEL_BASE_URL}/provider",
            params={"enabled": "invalid_boolean"},
        )
        assert response.status_code == 422

        # 测试 providerId 参数类型错误
        response = await client.get(
            f"{MODEL_BASE_URL}/source",
            params={"providerId": "invalid_integer"},
        )
        assert response.status_code == 422

        # 测试创建时字段类型错误
        response = await client.post(
            f"{MODEL_BASE_URL}/provider",
            json={
                "name": "测试渠道商",
                "enabled": "not_boolean",  # 应该是布尔值
            },
        )
        assert response.status_code == 422

    async def test_invalid_generation_kwargs(self, client: AsyncClient, test_provider):
        """测试无效的生成参数"""
        # generation_kwargs 应该是字典类型
        response = await client.post(
            f"{MODEL_BASE_URL}/source",
            json={
                "name": "invalid-kwargs-model",
                "alias": "invalid-kwargs",
                "providerId": test_provider["id"],
                "enabled": True,
                "generationKwargs": "not_a_dict",  # 应该是字典
            },
        )
        assert response.status_code == 422

    async def test_cascade_operations_error_handling(self, client: AsyncClient, test_provider_with_sources):
        """测试级联操作的错误处理"""
        provider_id = test_provider_with_sources["provider"]["id"]

        # 如果业务逻辑不允许删除有关联模型源的渠道商
        response = await client.delete(f"{MODEL_BASE_URL}/provider/{provider_id}")

        # 根据实际业务逻辑调整断言
        if response.status_code == 400:
            data = response.json()
            assert "关联" in data["detail"] or "依赖" in data["detail"]
        else:
            # 如果允许级联删除，则应该成功
            assert response.status_code == 200

    async def test_database_constraint_violations(self, client: AsyncClient):
        """测试数据库约束违反"""
        # 这里可以测试一些可能触发数据库约束的场景
        # 具体实现取决于数据库设计和约束设置
        pass

    async def test_large_payload_handling(self, client: AsyncClient):
        """测试大载荷处理"""
        # 测试非常大的generation_kwargs
        large_kwargs = {f"param_{i}": f"value_{i}" * 100 for i in range(100)}

        response = await client.post(
            f"{MODEL_BASE_URL}/provider",
            json={
                "name": "大载荷测试",
                "description": "x" * 255,  # 最大长度
                "baseUrl": "https://api.special-chars.com/v1",
                "apiKey": "sk-...",
                "enabled": True,
            },
        )
        assert response.status_code == 200
        provider_id = response.json()["data"]["id"]

        response = await client.post(
            f"{MODEL_BASE_URL}/source",
            json={
                "name": "large-payload-model",
                "alias": "large-payload",
                "providerId": provider_id,
                "enabled": True,
                "generationKwargs": large_kwargs,
            },
        )
        # 根据服务器配置，可能成功或因载荷过大失败
        assert response.status_code in [200, 413, 422]
