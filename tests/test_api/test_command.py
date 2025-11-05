import pytest
from httpx import AsyncClient


@pytest.fixture
async def test_category(client: AsyncClient):
    """创建测试用指令分类"""
    response = await client.post(
        "/api/v1/command/category",
        json={"name": "测试分类", "description": "测试分类描述"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "0000"
    return data["data"]


@pytest.fixture
async def test_command(client: AsyncClient, test_category):
    """创建测试用指令"""
    response = await client.post(
        "/api/v1/command/",
        json={
            "name": "测试指令",
            "code": "test_command",
            "categoryId": test_category["id"],
            "description": "测试指令描述",
            "commands": "测试|test",
            "isActive": True,
            "priority": 1,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "0000"
    return data["data"]


class TestCommandCategory:
    """指令分类测试"""

    async def test_create_category_success(self, client: AsyncClient):
        """测试创建分类成功"""
        response = await client.post(
            "/api/v1/command/category",
            json={"name": "系统指令", "description": "系统指令分类"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["name"] == "系统指令"
        assert data["data"]["description"] == "系统指令分类"

    async def test_create_category_duplicate(self, client: AsyncClient, test_category):
        """测试创建重复分类"""
        response = await client.post(
            "/api/v1/command/category",
            json={"name": test_category["name"], "description": "重复描述"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "已存在" in data["msg"]

    async def test_get_category_list(self, client: AsyncClient, test_category):
        """测试获取分类列表"""
        response = await client.get("/api/v1/command/category")
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
            "/api/v1/command/category", params={"nameOrDesc": "测试"}
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
                "/api/v1/command/category",
                json={"name": f"分类{i}", "description": f"描述{i}"},
            )

        # 测试分页
        response = await client.get(
            "/api/v1/command/category", params={"current": 1, "size": 3}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert len(data["data"]["categoryList"]) <= 3
        assert data["data"]["current"] == 1
        assert data["data"]["size"] == 3

    async def test_get_category_detail(self, client: AsyncClient, test_category):
        """测试获取分类详情"""
        response = await client.get(f"/api/v1/command/category/{test_category['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["id"] == test_category["id"]
        assert data["data"]["name"] == test_category["name"]

    async def test_get_category_detail_not_found(self, client: AsyncClient):
        """测试获取不存在的分类"""
        response = await client.get("/api/v1/command/category/99999")
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "不存在" in data["msg"]

    async def test_update_category_success(self, client: AsyncClient, test_category):
        """测试更新分类成功"""
        response = await client.put(
            f"/api/v1/command/category/{test_category['id']}",
            json={"name": "更新后的分类", "description": "更新后的描述"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "成功" in data["msg"]

    async def test_update_category_duplicate(self, client: AsyncClient):
        """测试更新分类为重复名称"""
        # 创建两个分类
        cat1 = await client.post(
            "/api/v1/command/category",
            json={"name": "分类A", "description": "描述A"},
        )
        cat1_data = cat1.json()["data"]

        cat2 = await client.post(
            "/api/v1/command/category",
            json={"name": "分类B", "description": "描述B"},
        )
        cat2_data = cat2.json()["data"]

        # 尝试将分类B更新为分类A的名称
        response = await client.put(
            f"/api/v1/command/category/{cat2_data['id']}",
            json={"name": "分类A", "description": "新描述"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "已存在" in data["msg"]

    async def test_update_category_not_found(self, client: AsyncClient):
        """测试更新不存在的分类"""
        response = await client.put(
            "/api/v1/command/category/99999",
            json={"name": "不存在", "description": "不存在"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "不存在" in data["msg"]

    async def test_delete_category_success(self, client: AsyncClient):
        """测试删除分类成功"""
        # 创建分类
        create_response = await client.post(
            "/api/v1/command/category",
            json={"name": "待删除分类", "description": "待删除"},
        )
        category_id = create_response.json()["data"]["id"]

        # 删除分类
        response = await client.delete(f"/api/v1/command/category/{category_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "成功" in data["msg"]

    async def test_delete_category_not_found(self, client: AsyncClient):
        """测试删除不存在的分类"""
        response = await client.delete("/api/v1/command/category/99999")
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "不存在" in data["msg"]

    async def test_delete_category_with_commands(
        self, client: AsyncClient, test_category, test_command
    ):
        """测试删除有关联指令的分类"""
        response = await client.delete(
            f"/api/v1/command/category/{test_category['id']}"
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "无法删除" in data["msg"]


class TestCommand:
    """指令测试"""

    async def test_create_command_success(self, client: AsyncClient, test_category):
        """测试创建指令成功"""
        response = await client.post(
            "/api/v1/command/",
            json={
                "name": "帮助指令",
                "code": "help",
                "categoryId": test_category["id"],
                "description": "显示帮助信息",
                "commands": "帮助|help|?",
                "isActive": True,
                "priority": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["name"] == "帮助指令"
        assert data["data"]["code"] == "help"
        assert data["data"]["priority"] == 10

    async def test_create_command_duplicate_name(
        self, client: AsyncClient, test_command
    ):
        """测试创建重复名称的指令"""
        response = await client.post(
            "/api/v1/command/",
            json={
                "name": test_command["name"],
                "code": "another_code",
                "categoryId": test_command["categoryId"],
                "commands": "test",
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "名称已存在" in data["msg"]

    async def test_create_command_duplicate_code(
        self, client: AsyncClient, test_command, test_category
    ):
        """测试创建重复代码的指令"""
        response = await client.post(
            "/api/v1/command/",
            json={
                "name": "另一个指令",
                "code": test_command["code"],
                "categoryId": test_category["id"],
                "commands": "test",
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "代码已存在" in data["msg"]

    async def test_create_command_invalid_category(self, client: AsyncClient):
        """测试创建指令时指定不存在的分类"""
        response = await client.post(
            "/api/v1/command/",
            json={
                "name": "测试指令",
                "code": "test",
                "categoryId": 99999,
                "commands": "test",
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "分类不存在" in data["msg"]

    async def test_get_command_list(self, client: AsyncClient, test_command):
        """测试获取指令列表"""
        response = await client.get("/api/v1/command/")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "commandList" in data["data"]
        assert data["data"]["total"] >= 1

    async def test_get_command_list_with_keyword(
        self, client: AsyncClient, test_command
    ):
        """测试按关键词搜索指令"""
        # 按名称搜索
        response = await client.get("/api/v1/command/", params={"keyword": "测试"})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 1

        # 按代码搜索
        response = await client.get(
            "/api/v1/command/", params={"keyword": test_command["code"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 1

    async def test_get_command_list_with_category(
        self, client: AsyncClient, test_command
    ):
        """测试按分类过滤指令"""
        response = await client.get(
            "/api/v1/command/", params={"categoryId": test_command["categoryId"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 1

    async def test_get_command_list_with_active_status(
        self, client: AsyncClient, test_category
    ):
        """测试按启用状态过滤指令"""
        # 创建启用和禁用的指令
        await client.post(
            "/api/v1/command/",
            json={
                "name": "启用指令",
                "code": "active_cmd",
                "categoryId": test_category["id"],
                "commands": "active",
                "isActive": True,
            },
        )
        await client.post(
            "/api/v1/command/",
            json={
                "name": "禁用指令",
                "code": "inactive_cmd",
                "categoryId": test_category["id"],
                "commands": "inactive",
                "isActive": False,
            },
        )

        # 测试过滤启用的指令
        response = await client.get("/api/v1/command/", params={"isActive": True})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 1

        # 测试过滤禁用的指令
        response = await client.get("/api/v1/command/", params={"isActive": False})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 1

    async def test_get_command_list_pagination(
        self, client: AsyncClient, test_category
    ):
        """测试指令列表分页"""
        # 创建多个指令
        for i in range(5):
            await client.post(
                "/api/v1/command/",
                json={
                    "name": f"指令{i}",
                    "code": f"cmd_{i}",
                    "categoryId": test_category["id"],
                    "commands": f"cmd{i}",
                },
            )

        # 测试分页
        response = await client.get(
            "/api/v1/command/", params={"current": 1, "size": 3}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert len(data["data"]["commandList"]) <= 3
        assert data["data"]["current"] == 1
        assert data["data"]["size"] == 3

    async def test_get_command_list_order_by_priority(
        self, client: AsyncClient, test_category
    ):
        """测试指令列表按优先级排序"""
        # 创建不同优先级的指令
        cmd_low = await client.post(
            "/api/v1/command/",
            json={
                "name": "低优先级",
                "code": "low_priority",
                "categoryId": test_category["id"],
                "commands": "low",
                "priority": 1,
            },
        )
        cmd_high = await client.post(
            "/api/v1/command/",
            json={
                "name": "高优先级",
                "code": "high_priority",
                "categoryId": test_category["id"],
                "commands": "high",
                "priority": 100,
            },
        )

        response = await client.get("/api/v1/command/")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"

        # 验证高优先级在前
        command_list = data["data"]["commandList"]
        high_index = next(
            i for i, cmd in enumerate(command_list) if cmd["code"] == "high_priority"
        )
        low_index = next(
            i for i, cmd in enumerate(command_list) if cmd["code"] == "low_priority"
        )
        assert high_index < low_index

    async def test_get_command_detail(self, client: AsyncClient, test_command):
        """测试获取指令详情"""
        response = await client.get(f"/api/v1/command/{test_command['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["id"] == test_command["id"]
        assert data["data"]["name"] == test_command["name"]
        assert "commands" in data["data"]

    async def test_get_command_detail_not_found(self, client: AsyncClient):
        """测试获取不存在的指令"""
        response = await client.get("/api/v1/command/99999")
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "不存在" in data["msg"]

    async def test_update_command_success(self, client: AsyncClient, test_command):
        """测试更新指令成功"""
        response = await client.put(
            f"/api/v1/command/{test_command['id']}",
            json={
                "name": "更新后的指令",
                "code": "updated_command",
                "description": "更新后的描述",
                "commands": "更新|update",
                "isActive": False,
                "priority": 50,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["name"] == "更新后的指令"
        assert data["data"]["code"] == "updated_command"

    async def test_update_command_not_found(self, client: AsyncClient):
        """测试更新不存在的指令"""
        response = await client.put(
            "/api/v1/command/99999",
            json={"name": "不存在的指令"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "不存在" in data["msg"]

    async def test_update_command_duplicate_name(
        self, client: AsyncClient, test_category
    ):
        """测试更新指令为重复名称"""
        # 创建两个指令
        cmd1 = await client.post(
            "/api/v1/command/",
            json={
                "name": "指令A",
                "code": "cmd_a",
                "categoryId": test_category["id"],
                "commands": "a",
            },
        )
        cmd1_data = cmd1.json()["data"]

        cmd2 = await client.post(
            "/api/v1/command/",
            json={
                "name": "指令B",
                "code": "cmd_b",
                "categoryId": test_category["id"],
                "commands": "b",
            },
        )
        cmd2_data = cmd2.json()["data"]

        # 尝试将指令B更新为指令A的名称
        response = await client.put(
            f"/api/v1/command/{cmd2_data['id']}",
            json={"name": "指令A"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "名称已存在" in data["msg"]

    async def test_update_command_duplicate_code(
        self, client: AsyncClient, test_category
    ):
        """测试更新指令为重复代码"""
        # 创建两个指令
        cmd1 = await client.post(
            "/api/v1/command/",
            json={
                "name": "指令A",
                "code": "cmd_a",
                "categoryId": test_category["id"],
                "commands": "a",
            },
        )
        cmd1_data = cmd1.json()["data"]

        cmd2 = await client.post(
            "/api/v1/command/",
            json={
                "name": "指令B",
                "code": "cmd_b",
                "categoryId": test_category["id"],
                "commands": "b",
            },
        )
        cmd2_data = cmd2.json()["data"]

        # 尝试将指令B更新为指令A的代码
        response = await client.put(
            f"/api/v1/command/{cmd2_data['id']}",
            json={"code": "cmd_a"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "代码已存在" in data["msg"]

    async def test_update_command_invalid_category(
        self, client: AsyncClient, test_command
    ):
        """测试更新指令时指定不存在的分类"""
        response = await client.put(
            f"/api/v1/command/{test_command['id']}",
            json={"categoryId": 99999},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "分类不存在" in data["msg"]

    async def test_delete_command_success(self, client: AsyncClient, test_category):
        """测试删除指令成功"""
        # 创建指令
        create_response = await client.post(
            "/api/v1/command/",
            json={
                "name": "待删除指令",
                "code": "to_delete",
                "categoryId": test_category["id"],
                "commands": "delete",
            },
        )
        command_id = create_response.json()["data"]["id"]

        # 删除指令
        response = await client.delete(f"/api/v1/command/{command_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "成功" in data["msg"]

    async def test_delete_command_not_found(self, client: AsyncClient):
        """测试删除不存在的指令"""
        response = await client.delete("/api/v1/command/99999")
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "不存在" in data["msg"]


class TestEdgeCases:
    """边界情况测试"""

    async def test_category_name_max_length(self, client: AsyncClient):
        """测试分类名称长度限制"""
        response = await client.get(
            "/api/v1/command/category", params={"nameOrDesc": "a" * 51}
        )
        # 应该会因为验证失败返回422
        assert response.status_code == 422

    async def test_keyword_max_length(self, client: AsyncClient):
        """测试关键词长度限制"""
        response = await client.get("/api/v1/command/", params={"keyword": "a" * 51})
        # 应该会因为验证失败返回422
        assert response.status_code == 422

    async def test_empty_list(self, client: AsyncClient):
        """测试空列表"""
        response = await client.get(
            "/api/v1/command/category", params={"nameOrDesc": "不存在的搜索词xyz123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] == 0
        assert len(data["data"]["categoryList"]) == 0

    async def test_command_variants(self, client: AsyncClient, test_category):
        """测试指令变体"""
        # 创建带有多个变体的指令
        response = await client.post(
            "/api/v1/command/",
            json={
                "name": "多变体指令",
                "code": "multi_variant",
                "categoryId": test_category["id"],
                "commands": "帮助|help|?|h",
                "description": "测试多个变体",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"

        # 获取指令详情，验证变体
        command_id = data["data"]["id"]
        detail_response = await client.get(f"/api/v1/command/{command_id}")
        assert detail_response.status_code == 200
        detail_data = detail_response.json()
        assert "commands" in detail_data["data"]
        assert "帮助" in detail_data["data"]["commands"]
        assert "help" in detail_data["data"]["commands"]

    async def test_command_without_category(self, client: AsyncClient):
        """测试创建不指定分类的指令"""
        response = await client.post(
            "/api/v1/command/",
            json={
                "name": "无分类指令",
                "code": "no_category",
                "commands": "test",
                "description": "不指定分类",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        # categoryId 应该为 None 或不存在
        assert data["data"].get("categoryId") is None

    async def test_update_command_partial(self, client: AsyncClient, test_command):
        """测试部分更新指令"""
        # 只更新描述
        response = await client.put(
            f"/api/v1/command/{test_command['id']}",
            json={"description": "仅更新描述"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["description"] == "仅更新描述"
        # 其他字段应该保持不变
        assert data["data"]["name"] == test_command["name"]
        assert data["data"]["code"] == test_command["code"]
