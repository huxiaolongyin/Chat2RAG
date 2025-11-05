import pytest
from httpx import AsyncClient


@pytest.fixture
async def test_category(client: AsyncClient):
    """创建测试用分类"""
    response = await client.post(
        "/api/v1/sensitive/category",
        json={"name": "测试分类", "description": "测试分类描述"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "0000"
    return data["data"]


@pytest.fixture
async def test_word(client: AsyncClient, test_category):
    """创建测试用敏感词"""
    response = await client.post(
        "/api/v1/sensitive/word",
        json={
            "word": "测试敏感词",
            "categoryId": test_category["id"],
            "level": 1,
            "description": "测试描述",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "0000"
    return data["data"]


class TestSensitiveCategory:
    """敏感词分类测试"""

    async def test_create_category_success(self, client: AsyncClient):
        """测试创建分类成功"""
        response = await client.post(
            "/api/v1/sensitive/category",
            json={"name": "违禁词", "description": "违禁词汇分类"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["name"] == "违禁词"
        assert data["data"]["description"] == "违禁词汇分类"

    async def test_create_category_duplicate(self, client: AsyncClient, test_category):
        """测试创建重复分类"""
        response = await client.post(
            "/api/v1/sensitive/category",
            json={"name": test_category["name"], "description": "重复描述"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "已存在" in data["msg"]

    async def test_get_category_list(self, client: AsyncClient, test_category):
        """测试获取分类列表"""
        response = await client.get("/api/v1/sensitive/category")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "categoryList" in data["data"]
        assert data["data"]["total"] >= 1
        assert len(data["data"]["categoryList"]) >= 1

    async def test_get_category_list_with_search(
        self, client: AsyncClient, test_category
    ):
        """测试搜索分类列表"""
        response = await client.get(
            "/api/v1/sensitive/category", params={"nameOrDesc": "测试"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 1

    async def test_get_category_list_pagination(self, client: AsyncClient):
        """测试分类列表分页"""
        # 创建多个分类
        for i in range(5):
            await client.post(
                "/api/v1/sensitive/category",
                json={"name": f"分类{i}", "description": f"描述{i}"},
            )

        # 测试分页
        response = await client.get(
            "/api/v1/sensitive/category", params={"current": 1, "size": 3}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert len(data["data"]["categoryList"]) <= 3
        assert data["data"]["current"] == 1
        assert data["data"]["size"] == 3

    async def test_get_category_detail(self, client: AsyncClient, test_category):
        """测试获取分类详情"""
        response = await client.get(f"/api/v1/sensitive/category/{test_category['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["id"] == test_category["id"]
        assert data["data"]["name"] == test_category["name"]

    async def test_get_category_detail_not_found(self, client: AsyncClient):
        """测试获取不存在的分类"""
        response = await client.get("/api/v1/sensitive/category/99999")
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "不存在" in data["msg"]

    async def test_update_category_success(self, client: AsyncClient, test_category):
        """测试更新分类成功"""
        response = await client.put(
            f"/api/v1/sensitive/category/{test_category['id']}",
            json={"name": "更新后的分类", "description": "更新后的描述"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["name"] == "更新后的分类"
        assert data["data"]["description"] == "更新后的描述"

    async def test_update_category_duplicate(self, client: AsyncClient):
        """测试更新分类为重复名称"""
        # 创建两个分类
        cat1 = await client.post(
            "/api/v1/sensitive/category",
            json={"name": "分类A", "description": "描述A"},
        )
        cat1_data = cat1.json()["data"]

        cat2 = await client.post(
            "/api/v1/sensitive/category",
            json={"name": "分类B", "description": "描述B"},
        )
        cat2_data = cat2.json()["data"]

        # 尝试将分类B更新为分类A的名称
        response = await client.put(
            f"/api/v1/sensitive/category/{cat2_data['id']}",
            json={"name": "分类A", "description": "新描述"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "已存在" in data["msg"]

    async def test_delete_category_success(self, client: AsyncClient):
        """测试删除分类成功"""
        # 创建分类
        create_response = await client.post(
            "/api/v1/sensitive/category",
            json={"name": "待删除分类", "description": "待删除"},
        )
        category_id = create_response.json()["data"]["id"]

        # 删除分类
        response = await client.delete(f"/api/v1/sensitive/category/{category_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "成功" in data["msg"]

    async def test_delete_category_not_found(self, client: AsyncClient):
        """测试删除不存在的分类"""
        response = await client.delete("/api/v1/sensitive/category/99999")
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "不存在" in data["msg"]


class TestSensitiveWord:
    """敏感词测试"""

    async def test_create_word_success(self, client: AsyncClient, test_category):
        """测试创建敏感词成功"""
        response = await client.post(
            "/api/v1/sensitive/word",
            json={
                "word": "敏感词1",
                "categoryId": test_category["id"],
                "level": 2,
                "description": "敏感词描述",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["word"] == "敏感词1"
        assert data["data"]["level"] == 2

    async def test_create_word_duplicate(self, client: AsyncClient, test_word):
        """测试创建重复敏感词"""
        response = await client.post(
            "/api/v1/sensitive/word",
            json={
                "word": test_word["word"],
                "categoryId": test_word["categoryId"],
                "level": 1,
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "已存在" in data["msg"]

    async def test_get_word_list(self, client: AsyncClient, test_word):
        """测试获取敏感词列表"""
        response = await client.get("/api/v1/sensitive/word")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "wordList" in data["data"]
        assert data["data"]["total"] >= 1

    async def test_get_word_list_with_filters(self, client: AsyncClient, test_word):
        """测试过滤敏感词列表"""
        # 按词搜索
        response = await client.get("/api/v1/sensitive/word", params={"word": "测试"})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"

        # 按分类过滤
        response = await client.get(
            "/api/v1/sensitive/word", params={"categoryId": test_word["categoryId"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 1

        # 按级别过滤
        response = await client.get("/api/v1/sensitive/word", params={"level": 1})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"

    async def test_get_word_list_pagination(self, client: AsyncClient, test_category):
        """测试敏感词列表分页"""
        # 创建多个敏感词
        for i in range(5):
            await client.post(
                "/api/v1/sensitive/word",
                json={
                    "word": f"敏感词{i}",
                    "categoryId": test_category["id"],
                    "level": 1,
                },
            )

        # 测试分页
        response = await client.get(
            "/api/v1/sensitive/word", params={"current": 1, "size": 3}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert len(data["data"]["wordList"]) <= 3

    async def test_get_word_detail(self, client: AsyncClient, test_word):
        """测试获取敏感词详情"""
        response = await client.get(f"/api/v1/sensitive/word/{test_word['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["id"] == test_word["id"]
        assert data["data"]["word"] == test_word["word"]

    async def test_get_word_detail_not_found(self, client: AsyncClient):
        """测试获取不存在的敏感词"""
        response = await client.get("/api/v1/sensitive/word/99999")
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "不存在" in data["msg"]

    async def test_update_word_success(self, client: AsyncClient, test_word):
        """测试更新敏感词成功"""
        response = await client.put(
            f"/api/v1/sensitive/word/{test_word['id']}",
            json={
                "word": "更新后的敏感词",
                "categoryId": test_word["categoryId"],
                "level": 3,
                "description": "更新后的描述",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["word"] == "更新后的敏感词"
        assert data["data"]["level"] == 3

    async def test_update_word_not_found(self, client: AsyncClient, test_category):
        """测试更新不存在的敏感词"""
        response = await client.put(
            "/api/v1/sensitive/word/99999",
            json={
                "word": "不存在的词",
                "categoryId": test_category["id"],
                "level": 1,
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "不存在" in data["msg"]

    async def test_update_word_duplicate(self, client: AsyncClient, test_category):
        """测试更新敏感词为重复名称"""
        # 创建两个敏感词
        word1 = await client.post(
            "/api/v1/sensitive/word",
            json={"word": "敏感词A", "categoryId": test_category["id"], "level": 1},
        )
        word1_data = word1.json()["data"]

        word2 = await client.post(
            "/api/v1/sensitive/word",
            json={"word": "敏感词B", "categoryId": test_category["id"], "level": 1},
        )
        word2_data = word2.json()["data"]

        # 尝试将敏感词B更新为敏感词A
        response = await client.put(
            f"/api/v1/sensitive/word/{word2_data['id']}",
            json={
                "word": "敏感词A",
                "categoryId": test_category["id"],
                "level": 1,
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "已存在" in data["msg"]

    async def test_delete_word_success(self, client: AsyncClient, test_category):
        """测试删除敏感词成功"""
        # 创建敏感词
        create_response = await client.post(
            "/api/v1/sensitive/word",
            json={
                "word": "待删除敏感词",
                "categoryId": test_category["id"],
                "level": 1,
            },
        )
        word_id = create_response.json()["data"]["id"]

        # 删除敏感词
        response = await client.delete(f"/api/v1/sensitive/word/{word_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "成功" in data["msg"]

    async def test_delete_word_not_found(self, client: AsyncClient):
        """测试删除不存在的敏感词"""
        response = await client.delete("/api/v1/sensitive/word/99999")
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "不存在" in data["msg"]


class TestEdgeCases:
    """边界情况测试"""

    async def test_category_name_max_length(self, client: AsyncClient):
        """测试分类名称长度限制"""
        response = await client.get(
            "/api/v1/sensitive/category", params={"nameOrDesc": "a" * 11}
        )
        # 应该会因为验证失败返回422
        assert response.status_code == 422

    async def test_word_max_length(self, client: AsyncClient):
        """测试敏感词长度限制"""
        response = await client.get("/api/v1/sensitive/word", params={"word": "a" * 51})
        # 应该会因为验证失败返回422
        assert response.status_code == 422

    async def test_level_validation(self, client: AsyncClient):
        """测试级别验证"""
        # 测试超出范围的级别
        response = await client.get("/api/v1/sensitive/word", params={"level": 4})
        assert response.status_code == 422

        response = await client.get("/api/v1/sensitive/word", params={"level": 0})
        assert response.status_code == 422

    async def test_empty_list(self, client: AsyncClient):
        """测试空列表"""
        response = await client.get(
            "/api/v1/sensitive/category", params={"nameOrDesc": "不存在的搜索词"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] == 0
        assert len(data["data"]["categoryList"]) == 0
