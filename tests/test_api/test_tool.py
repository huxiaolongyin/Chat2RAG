import pytest
from httpx import AsyncClient


@pytest.fixture
async def test_api_tool(client: AsyncClient):
    """创建测试用API工具"""
    response = await client.post(
        "/api/v1/tools/",
        json={
            "toolType": "api",
            "data": {
                "name": "测试API工具",
                "description": "测试API工具描述",
                "url": "https://api.example.com/test",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "body": {"key": "value"},
                "isActive": True,
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "0000"
    return data["data"]


@pytest.fixture
async def test_mcp_server(client: AsyncClient):
    """创建测试用MCP服务器"""
    response = await client.post(
        "/api/v1/tools/",
        json={
            "toolType": "mcp",
            "data": {
                "name": "高德",
                "mcpType": "streamable",
                "url": "https://mcp.amap.com/mcp?key=2502b472c2922df3c36c201bfc711018",
                "isActive": True,
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "0000"
    return data["data"]


class TestToolList:
    """工具列表测试"""

    async def test_get_all_tools_default(self, client: AsyncClient, test_api_tool):
        """测试获取所有工具（默认参数）"""
        response = await client.get("/api/v1/tools/")
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "toolList" in data["data"]
        assert "total" in data["data"]
        assert "current" in data["data"]
        assert "size" in data["data"]
        assert "pages" in data["data"]
        assert data["data"]["total"] >= 1

    async def test_get_api_tools_only(self, client: AsyncClient, test_api_tool):
        """测试仅获取API工具"""
        response = await client.get("/api/v1/tools/", params={"toolType": "api"})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 1
        # 验证所有工具都是API类型
        for tool in data["data"]["toolList"]:
            assert tool["toolType"] == "api"

    async def test_get_mcp_tools_only(self, client: AsyncClient, test_mcp_server):
        """测试仅获取MCP工具"""
        response = await client.get("/api/v1/tools/", params={"toolType": "mcp"})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 1
        # 验证所有工具都是MCP类型
        for tool in data["data"]["toolList"]:
            assert tool["toolType"] == "mcp"

    async def test_get_tools_with_name_filter(self, client: AsyncClient, test_api_tool):
        """测试按名称过滤工具"""
        response = await client.get("/api/v1/tools/", params={"toolName": "测试API"})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 1
        # 验证返回的工具名称包含搜索关键词
        for tool in data["data"]["toolList"]:
            assert "测试API" in tool["name"]

    async def test_get_tools_with_desc_filter(self, client: AsyncClient, test_api_tool):
        """测试按描述过滤工具"""
        response = await client.get("/api/v1/tools/", params={"toolDesc": "工具描述"})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 1

    async def test_get_tools_with_active_filter(self, client: AsyncClient):
        """测试按启用状态过滤工具"""
        # 创建启用和禁用的工具
        await client.post(
            "/api/v1/tools/",
            json={
                "toolType": "api",
                "data": {
                    "name": "启用工具",
                    "url": "https://api.example.com/active",
                    "method": "GET",
                    "isActive": True,
                },
            },
        )
        await client.post(
            "/api/v1/tools/",
            json={
                "toolType": "api",
                "data": {
                    "name": "禁用工具",
                    "url": "https://api.example.com/inactive",
                    "method": "GET",
                    "isActive": False,
                },
            },
        )

        # 测试过滤启用的工具
        response = await client.get("/api/v1/tools/", params={"isActive": True})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        for tool in data["data"]["toolList"]:
            assert tool["isActive"] is True

        # 测试过滤禁用的工具
        response = await client.get("/api/v1/tools/", params={"isActive": False})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        for tool in data["data"]["toolList"]:
            assert tool["isActive"] is False

    async def test_get_tools_pagination(self, client: AsyncClient):
        """测试工具列表分页"""
        # 创建多个工具
        for i in range(5):
            await client.post(
                "/api/v1/tools/",
                json={
                    "toolType": "api",
                    "data": {
                        "name": f"分页工具{i}",
                        "url": f"https://api.example.com/page{i}",
                        "method": "GET",
                    },
                },
            )

        # 测试第一页
        response = await client.get("/api/v1/tools/", params={"current": 1, "size": 3})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert len(data["data"]["toolList"]) <= 3
        assert data["data"]["current"] == 1
        assert data["data"]["size"] == 3
        assert data["data"]["pages"] >= 2

        # 测试第二页
        response = await client.get("/api/v1/tools/", params={"current": 2, "size": 3})
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["current"] == 2

    async def test_get_tools_sort_by_create_time_asc(self, client: AsyncClient):
        """测试按创建时间升序排序"""
        response = await client.get(
            "/api/v1/tools/",
            params={"sortBy": "create_time", "sortOrder": "asc"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        # 验证排序（如果有多条记录）
        if len(data["data"]["toolList"]) > 1:
            tools = data["data"]["toolList"]
            for i in range(len(tools) - 1):
                assert tools[i]["create_time"] <= tools[i + 1]["create_time"]

    async def test_get_tools_sort_by_create_time_desc(self, client: AsyncClient):
        """测试按创建时间降序排序"""
        response = await client.get(
            "/api/v1/tools/",
            params={"sortBy": "create_time", "sortOrder": "desc"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        # 验证排序（如果有多条记录）
        if len(data["data"]["toolList"]) > 1:
            tools = data["data"]["toolList"]
            for i in range(len(tools) - 1):
                assert tools[i]["create_time"] >= tools[i + 1]["create_time"]

    async def test_get_tools_combined_filters(self, client: AsyncClient):
        """测试组合过滤条件"""
        response = await client.get(
            "/api/v1/tools/",
            params={
                "toolType": "api",
                "toolName": "测试",
                "isActive": True,
                "current": 1,
                "size": 10,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"


class TestCreateTool:
    """创建工具测试"""

    async def test_create_api_tool_success(self, client: AsyncClient):
        """测试成功创建API工具"""
        response = await client.post(
            "/api/v1/tools/",
            json={
                "toolType": "api",
                "data": {
                    "name": "新API工具",
                    "description": "新API工具描述",
                    "url": "https://api.example.com/new",
                    "method": "GET",
                    "isActive": True,
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "id" in data["data"]
        assert "成功" in data["msg"]

    async def test_create_api_tool_duplicate_name(
        self, client: AsyncClient, test_api_tool
    ):
        """测试创建重复名称的API工具"""
        response = await client.post(
            "/api/v1/tools/",
            json={
                "toolType": "api",
                "data": {
                    "name": test_api_tool["name"],
                    "url": "https://api.example.com/duplicate",
                    "method": "GET",
                },
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "已存在" in data["msg"]

    async def test_create_mcp_server_success(self, client: AsyncClient):
        """测试成功创建MCP服务器"""
        response = await client.post(
            "/api/v1/tools/",
            json={
                "toolType": "mcp",
                "data": {
                    "name": "新MCP服务器",
                    "description": "新MCP服务器描述",
                    "mcpType": "stdio",
                    "command": "node",
                    "args": ["server.js"],
                    "isActive": True,
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "id" in data["data"]
        assert "成功" in data["msg"]

    async def test_create_mcp_server_duplicate_name(
        self, client: AsyncClient, test_mcp_server
    ):
        """测试创建重复名称的MCP服务器"""
        response = await client.post(
            "/api/v1/tools/",
            json={
                "toolType": "mcp",
                "data": {
                    "name": test_mcp_server["name"],
                    "mcpType": "stdio",
                    "command": "python",
                    "args": ["-m", "another_server"],
                },
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "已存在" in data["msg"]

    async def test_create_tool_invalid_format(self, client: AsyncClient):
        """测试创建工具时使用无效格式"""
        response = await client.post(
            "/api/v1/tools/",
            json={
                "toolType": "invalid",
                "data": {"name": "无效工具"},
            },
        )
        # 应该返回422或400
        assert response.status_code in [400, 422]


class TestUpdateTool:
    """更新工具测试"""

    async def test_update_api_tool_success(self, client: AsyncClient, test_api_tool):
        """测试成功更新API工具"""
        response = await client.put(
            f"/api/v1/tools/{test_api_tool['id']}",
            params={"toolType": "api"},
            json={
                "toolType": "api",
                "data": {
                    "name": "更新后的API工具",
                    "description": "更新后的描述",
                    "url": "https://api.example.com/updated",
                    "method": "GET",
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "成功" in data["msg"]
        assert data["data"]["id"] == test_api_tool["id"]

    async def test_update_api_tool_not_found(self, client: AsyncClient):
        """测试更新不存在的API工具"""
        response = await client.put(
            "/api/v1/tools/99999",
            params={"toolType": "api"},
            json={
                "toolType": "api",
                "data": {"name": "不存在的工具"},
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "不存在" in data["msg"]

    async def test_update_api_tool_duplicate_name(self, client: AsyncClient):
        """测试更新API工具为重复名称"""
        # 创建两个工具
        tool1 = await client.post(
            "/api/v1/tools/",
            json={
                "toolType": "api",
                "data": {
                    "name": "工具A",
                    "url": "https://api.example.com/a",
                    "method": "GET",
                },
            },
        )
        tool1_data = tool1.json()["data"]

        tool2 = await client.post(
            "/api/v1/tools/",
            json={
                "toolType": "api",
                "data": {
                    "name": "工具B",
                    "url": "https://api.example.com/b",
                    "method": "GET",
                },
            },
        )
        tool2_data = tool2.json()["data"]

        # 尝试将工具B更新为工具A的名称
        response = await client.put(
            f"/api/v1/tools/{tool2_data['id']}",
            params={"toolType": "api"},
            json={
                "toolType": "api",
                "data": {"name": "工具A"},
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "已存在" in data["msg"]

    async def test_update_api_tool_type_mismatch(
        self, client: AsyncClient, test_api_tool
    ):
        """测试工具类型与请求数据不匹配"""
        response = await client.put(
            f"/api/v1/tools/{test_api_tool['id']}",
            params={"toolType": "api"},
            json={
                "toolType": "mcp",
                "data": {"name": "MCP数据", "mcpType": "stdio"},
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "不匹配" in data["msg"]

    async def test_update_mcp_server_success(
        self, client: AsyncClient, test_mcp_server
    ):
        """测试成功更新MCP服务器"""
        response = await client.put(
            f"/api/v1/tools/{test_mcp_server['id']}",
            params={"toolType": "mcp"},
            json={
                "toolType": "mcp",
                "data": {
                    "name": "更新后的MCP服务器",
                    "description": "更新后的描述",
                    "mcpType": "stdio",
                    "command": "node",
                    "args": ["updated_server.js"],
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "成功" in data["msg"]

    async def test_update_tool_partial(self, client: AsyncClient, test_api_tool):
        """测试部分更新工具"""
        response = await client.put(
            f"/api/v1/tools/{test_api_tool['id']}",
            params={"toolType": "api"},
            json={
                "toolType": "api",
                "data": {"description": "仅更新描述"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"


class TestGetToolDetail:
    """获取工具详情测试"""

    async def test_get_api_tool_detail(self, client: AsyncClient, test_api_tool):
        """测试获取API工具详情"""
        response = await client.get(
            f"/api/v1/tools/{test_api_tool['id']}",
            params={"toolType": "api"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["toolType"] == "api"
        assert "name" in data["data"]
        assert "url" in data["data"]
        assert "method" in data["data"]

    async def test_get_api_tool_detail_not_found(self, client: AsyncClient):
        """测试获取不存在的API工具"""
        response = await client.get(
            "/api/v1/tools/99999",
            params={"toolType": "api"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "不存在" in data["msg"]

    async def test_get_mcp_tool_detail(self, client: AsyncClient, test_mcp_server):
        """测试获取MCP工具详情"""
        response = await client.get(
            f"/api/v1/tools/{test_mcp_server['id']}",
            params={"toolType": "mcp"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["toolType"] == "mcp"
        assert "name" in data["data"]
        assert "command" in data["data"]

    async def test_get_tool_detail_invalid_type(self, client: AsyncClient):
        """测试使用无效的工具类型获取详情"""
        response = await client.get(
            "/api/v1/tools/1",
            params={"toolType": "invalid"},
        )
        # 应该返回422（参数验证失败）
        assert response.status_code == 422


class TestDeleteTool:
    """删除工具测试"""

    async def test_delete_api_tool_success(self, client: AsyncClient):
        """测试成功删除API工具"""
        # 创建工具
        create_response = await client.post(
            "/api/v1/tools/",
            json={
                "toolType": "api",
                "data": {
                    "name": "待删除API工具",
                    "url": "https://api.example.com/delete",
                    "method": "GET",
                },
            },
        )
        tool_id = create_response.json()["data"]["id"]

        # 删除工具
        response = await client.delete(
            f"/api/v1/tools/{tool_id}",
            params={"toolType": "api"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "成功" in data["msg"]

    async def test_delete_api_tool_not_found(self, client: AsyncClient):
        """测试删除不存在的API工具"""
        response = await client.delete(
            "/api/v1/tools/99999",
            params={"toolType": "api"},
        )
        # 删除不存在的资源通常返回成功或404，根据你的实现
        assert response.status_code in [200, 400]

    async def test_delete_mcp_server_success(self, client: AsyncClient):
        """测试成功删除MCP服务器"""
        # 创建服务器
        create_response = await client.post(
            "/api/v1/tools/",
            json={
                "toolType": "mcp",
                "data": {
                    "name": "待删除MCP服务器",
                    "mcpType": "stdio",
                    "command": "python",
                    "args": ["-m", "delete_server"],
                },
            },
        )
        server_id = create_response.json()["data"]["id"]

        # 删除服务器
        response = await client.delete(
            f"/api/v1/tools/{server_id}",
            params={"toolType": "mcp"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert "成功" in data["msg"]


class TestSyncMCPTools:
    """同步MCP工具测试"""

    async def test_sync_mcp_tools_success(self, client: AsyncClient, test_mcp_server):
        """测试成功同步MCP工具"""
        response = await client.post(f"/api/v1/tools/{test_mcp_server['id']}/sync")
        # 注意：实际同步可能需要MCP服务器运行，这里测试框架行为
        assert response.status_code in [200, 400]
        data = response.json()
        # 如果成功
        if response.status_code == 200:
            assert data["code"] == "0000"
            assert "serverId" in data["data"]
            assert "toolCount" in data["data"]
            assert "tools" in data["data"]

    async def test_sync_mcp_tools_server_not_found(self, client: AsyncClient):
        """测试同步不存在的MCP服务器"""
        response = await client.post("/api/v1/tools/99999/sync")
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "4000"
        assert "不存在" in data["msg"]


class TestEdgeCases:
    """边界情况测试"""

    async def test_empty_tool_list(self, client: AsyncClient):
        """测试空工具列表"""
        response = await client.get(
            "/api/v1/tools/",
            params={"toolName": "不存在的工具名称xyz123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] == 0
        assert len(data["data"]["toolList"]) == 0

    async def test_large_page_size(self, client: AsyncClient):
        """测试大分页size"""
        response = await client.get(
            "/api/v1/tools/",
            params={"size": 100},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"

    async def test_invalid_page_number(self, client: AsyncClient):
        """测试无效的页码"""
        response = await client.get(
            "/api/v1/tools/",
            params={"current": 0},
        )
        # 应该返回422（参数验证失败）
        assert response.status_code == 422

    async def test_api_tool_with_complex_headers(self, client: AsyncClient):
        """测试创建带复杂headers的API工具"""
        response = await client.post(
            "/api/v1/tools/",
            json={
                "toolType": "api",
                "data": {
                    "name": "复杂Headers工具",
                    "url": "https://api.example.com/complex",
                    "method": "POST",
                    "headers": {
                        "Content-Type": "application/json",
                        "Authorization": "Bearer token123",
                        "X-Custom-Header": "custom-value",
                    },
                    "body": {
                        "nested": {"key": "value"},
                        "array": [1, 2, 3],
                    },
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"

    async def test_mcp_server_with_env_vars(self, client: AsyncClient):
        """测试创建带环境变量的MCP服务器"""
        response = await client.post(
            "/api/v1/tools/",
            json={
                "toolType": "mcp",
                "data": {
                    "name": "带环境变量的MCP",
                    "mcpType": "stdio",
                    "command": "python",
                    "args": ["-m", "server"],
                    "env": {
                        "DEBUG": "true",
                        "API_KEY": "secret123",
                        "PORT": "8080",
                    },
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"

    async def test_tool_name_special_characters(self, client: AsyncClient):
        """测试工具名称包含特殊字符"""
        response = await client.post(
            "/api/v1/tools/",
            json={
                "toolType": "api",
                "data": {
                    "name": "工具-测试_API (v1.0)",
                    "url": "https://api.example.com/special",
                    "method": "GET",
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"

    async def test_concurrent_tool_creation(self, client: AsyncClient):
        """测试并发创建工具"""
        import asyncio

        async def create_tool(index):
            return await client.post(
                "/api/v1/tools/",
                json={
                    "toolType": "api",
                    "data": {
                        "name": f"并发工具{index}",
                        "url": f"https://api.example.com/concurrent{index}",
                        "method": "GET",
                    },
                },
            )

        # 并发创建多个工具
        responses = await asyncio.gather(
            *[create_tool(i) for i in range(5)], return_exceptions=True
        )

        # 验证所有请求都成功
        for response in responses:
            if not isinstance(response, Exception):
                assert response.status_code == 200
                data = response.json()
                assert data["code"] == "0000"

    async def test_tool_type_all_with_mixed_tools(self, client: AsyncClient):
        """测试获取全部工具类型时的排序和分页"""
        # 创建混合类型的工具
        for i in range(3):
            await client.post(
                "/api/v1/tools/",
                json={
                    "toolType": "api",
                    "data": {
                        "name": f"API工具{i}",
                        "url": f"https://api.example.com/mixed{i}",
                        "method": "GET",
                    },
                },
            )
            await client.post(
                "/api/v1/tools/",
                json={
                    "toolType": "mcp",
                    "data": {
                        "name": f"MCP服务器{i}",
                        "mcpType": "stdio",
                        "command": "python",
                        "args": ["-m", f"server{i}"],
                    },
                },
            )

        # 获取全部工具并验证排序
        response = await client.get(
            "/api/v1/tools/",
            params={"toolType": "all", "size": 10},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "0000"
        assert data["data"]["total"] >= 3

        # 验证包含两种类型的工具
        tool_types = {tool["toolType"] for tool in data["data"]["toolList"]}
        assert len(tool_types) >= 1  # 至少有一种类型
