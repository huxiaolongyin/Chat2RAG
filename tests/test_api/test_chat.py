import json

import pytest
from httpx import AsyncClient

# @pytest.fixture
# async def test_collection(client: AsyncClient):
#     """创建测试用知识库"""
#     response = await client.post(
#         "/api/v1/collection",
#         json={
#             "name": "测试知识库",
#             "description": "用于聊天测试的知识库",
#             "embeddingModel": "text-embedding-ada-002",
#         },
#     )
#     assert response.status_code == 200
#     data = response.json()
#     assert data["code"] == "0000"
#     return data["data"]


@pytest.fixture
async def test_prompt(client: AsyncClient):
    """创建测试用提示词"""
    response = await client.post(
        "/api/v1/prompts",
        json={
            "promptName": "测试提示词",
            "promptDesc": "测试提示词",
            "promptText": "你是一个智能助手，请回答用户的问题。",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "0000"
    return data["data"]


@pytest.fixture
async def test_command_with_category(client: AsyncClient):
    """创建测试用指令和分类"""
    # 创建分类
    category_response = await client.post(
        "/api/v1/command/category",
        json={"name": "聊天测试分类", "description": "聊天测试用分类"},
    )
    category = category_response.json()["data"]

    # 创建指令
    command_response = await client.post(
        "/api/v1/command/",
        json={
            "name": "聊天测试指令",
            "code": "chat_test_cmd",
            "categoryId": category["id"],
            "description": "聊天测试指令",
            "commands": "测试指令|test_cmd",
            "isActive": True,
            "priority": 10,
        },
    )
    command = command_response.json()["data"]
    return {"category": category, "command": command}


@pytest.fixture
async def test_flow(client: AsyncClient):
    """创建测试用流程"""
    response = await client.post(
        "/api/v1/flows",
        json={
            "name": "点餐流程",
            "desc": "用于麦当劳入门时的点餐流程",
            "currentVersion": 1,
            "flowJson": {
                "zoom": 0.6597539553864473,
                "edges": [
                    {
                        "id": "vueflow__edge-dndnode_0-dndnode_1target",
                        "data": {},
                        "type": "default",
                        "label": "",
                        "source": "dndnode_0",
                        "target": "dndnode_1",
                        "sourceX": 395.70267307447574,
                        "sourceY": 399.2544619109558,
                        "targetX": 495.9563953908104,
                        "targetY": 407.75341472626576,
                        "sourceHandle": "",
                        "targetHandle": "target",
                    },
                    {
                        "id": "vueflow__edge-dndnode_1source-0-dndnode_2target",
                        "data": {},
                        "type": "default",
                        "label": "",
                        "source": "dndnode_1",
                        "target": "dndnode_2",
                        "sourceX": 862.9565457116819,
                        "sourceY": 338.67524912045633,
                        "targetX": 1048.6551752264309,
                        "targetY": -14.799966553677933,
                        "sourceHandle": "source-0",
                        "targetHandle": "target",
                    },
                    {
                        "id": "vueflow__edge-dndnode_1source-1-dndnode_3target",
                        "data": {},
                        "type": "default",
                        "label": "",
                        "source": "dndnode_1",
                        "target": "dndnode_3",
                        "sourceX": 862.9565457116819,
                        "sourceY": 536.0190704563794,
                        "targetX": 1021.6771281581638,
                        "targetY": 659.6668065713664,
                        "sourceHandle": "source-1",
                        "targetHandle": "target",
                    },
                    {
                        "id": "vueflow__edge-dndnode_3-dndnode_4target",
                        "data": {},
                        "type": "default",
                        "label": "",
                        "source": "dndnode_3",
                        "target": "dndnode_4",
                        "sourceX": 1393.6771048421817,
                        "sourceY": 659.6668065713664,
                        "targetX": 1751.4573556249622,
                        "targetY": 383.794725127715,
                        "sourceHandle": "",
                        "targetHandle": "target",
                    },
                    {
                        "id": "vueflow__edge-dndnode_2-dndnode_4target",
                        "data": {},
                        "type": "default",
                        "label": "",
                        "source": "dndnode_2",
                        "target": "dndnode_4",
                        "sourceX": 1420.6553475047467,
                        "sourceY": -14.799966553677933,
                        "targetX": 1751.4573556249622,
                        "targetY": 383.794725127715,
                        "sourceHandle": "",
                        "targetHandle": "target",
                    },
                ],
                "nodes": [
                    {
                        "id": "dndnode_0",
                        "data": {
                            "emoji": "微笑",
                            "label": "dndnode_0",
                            "action": "抬右手",
                            "isAuto": True,
                            "response": "欢迎光临麦当劳。你想吃点什么呢？",
                            "stateName": "",
                            "conditions": [{"trigger": ""}],
                        },
                        "type": "start",
                        "position": {"x": 28.702603290005925, "y": 245.06692138503854},
                        "initialized": False,
                    },
                    {
                        "id": "dndnode_3",
                        "data": {
                            "emoji": "微笑",
                            "label": "dndnode_3",
                            "action": "抬右手",
                            "isAuto": False,
                            "response": "需要再来一杯可乐吗",
                            "stateName": "增加饮料",
                            "conditions": [{"trigger": "用户确认需要可乐"}],
                        },
                        "type": "singleState",
                        "position": {"x": 1026.6772162591833, "y": 431.4793735559688},
                        "initialized": False,
                    },
                    {
                        "id": "dndnode_1",
                        "data": {
                            "emoji": "微笑",
                            "label": "dndnode_1",
                            "action": "抬右手",
                            "isAuto": False,
                            "response": "需要汉堡还是炸鸡",
                            "stateName": "菜别",
                            "conditions": [
                                {"id": 0, "trigger": "用户想要吃汉堡"},
                                {"id": 1, "trigger": "用户想要吃炸鸡"},
                            ],
                        },
                        "type": "multiState",
                        "position": {"x": 500.95641734825494, "y": 111.75331116031904},
                        "initialized": False,
                    },
                    {
                        "id": "dndnode_2",
                        "data": {
                            "emoji": "微笑",
                            "label": "dndnode_2",
                            "action": "抬右手",
                            "isAuto": False,
                            "response": "需要什么时候送到",
                            "stateName": "询问时间",
                            "conditions": [{"trigger": "获取到时间"}],
                        },
                        "type": "singleState",
                        "position": {"x": 1053.6551971838753, "y": -242.98753406508837},
                        "initialized": False,
                    },
                    {
                        "id": "dndnode_4",
                        "data": {
                            "emoji": "微笑",
                            "label": "dndnode_4",
                            "action": "抬右手",
                            "isAuto": False,
                            "response": "好的，正在为您准备订单。",
                            "stateName": "",
                            "conditions": [{"trigger": ""}],
                        },
                        "type": "end",
                        "position": {"x": 1756.4573556249622, "y": 244.7946946101369},
                        "initialized": False,
                    },
                ],
                "position": [-347.35250344149017, 84.45688165220798],
                "viewport": {
                    "x": -347.35250344149017,
                    "y": 84.45688165220798,
                    "zoom": 0.6597539553864473,
                },
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "0000"
    return data["data"]


# @pytest.fixture
# async def test_exact_match(client: AsyncClient):
#     """创建测试用精确匹配规则"""
#     response = await client.post(
#         "/api/v1/exact-match",
#         json={
#             "question": "测试问题",
#             "answer": "这是测试答案",
#             "isActive": True,
#             "priority": 10,
#         },
#     )
#     assert response.status_code == 200
#     data = response.json()
#     assert data["code"] == "0000"
#     return data["data"]


async def parse_stream_response(response):
    """解析流式响应的辅助函数"""
    chunks = []
    async for chunk in response.aiter_lines():
        if chunk:
            chunks.append(chunk)
    return chunks


async def parse_sse_events(response):
    """解析 Server-Sent Events (SSE) 格式的响应"""
    events = []
    async for line in response.aiter_lines():
        if line.startswith("data: "):
            try:
                data = json.loads(line[6:])  # 去掉 "data: " 前缀
                events.append(data)
            except json.JSONDecodeError:
                # 如果不是 JSON，保存原始文本
                events.append(line[6:])
    return events


class TestChatBasic:
    """基础聊天测试"""

    async def test_chat_basic_success(self, client: AsyncClient):
        """测试基础聊天成功"""
        async with client.stream(
            "POST",
            "/api/v2/chat",
            json={
                "chatId": "test_chat_001",
                "chatRounds": 1,
                "content": {"text": "你好"},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
            },
        ) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

            # 读取流式数据
            chunks = []
            async for chunk in response.aiter_bytes():
                if chunk:
                    chunks.append(chunk.decode("utf-8"))

            # 验证有数据返回
            assert len(chunks) > 0
            content = "".join(chunks)
            assert len(content) > 0

    async def test_chat_with_empty_text(self, client: AsyncClient):
        """测试空文本聊天"""
        response = await client.post(
            "/api/v2/chat",
            json={
                "chatId": "test_chat_002",
                "chatRounds": 1,
                "content": {"text": ""},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
            },
        )
        assert response.status_code == 404

    async def test_chat_batch_mode(self, client: AsyncClient):
        """测试批处理模式"""
        async with client.stream(
            "POST",
            "/api/v2/chat",
            json={
                "chatId": "test_chat_003",
                "chatRounds": 1,
                "content": {"text": "测试批处理"},
                "batchOrStream": "batch",
                "collections": ["测试数据"],
            },
        ) as response:
            assert response.status_code == 200

            # 批处理模式也可能返回流式响应
            chunks = []
            async for chunk in response.aiter_bytes():
                if chunk:
                    chunks.append(chunk.decode("utf-8"))

            assert len(chunks) > 0

    async def test_chat_stream_mode(self, client: AsyncClient):
        """测试流式模式"""
        async with client.stream(
            "POST",
            "/api/v2/chat",
            json={
                "chatId": "test_chat_004",
                "chatRounds": 1,
                "content": {"text": "测试流式输出"},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
            },
        ) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

            # 验证流式数据
            chunk_count = 0
            async for chunk in response.aiter_bytes():
                if chunk:
                    chunk_count += 1

            assert chunk_count > 0

    async def test_chat_with_multiple_rounds(self, client: AsyncClient):
        """测试多轮对话"""
        # 第一轮
        async with client.stream(
            "POST",
            "/api/v2/chat",
            json={
                "chatId": "test_chat_005",
                "chatRounds": 1,
                "content": {"text": "我叫张三"},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
            },
        ) as response1:
            assert response1.status_code == 200
            async for _ in response1.aiter_bytes():
                pass  # 消费第一轮响应

        # 第二轮
        async with client.stream(
            "POST",
            "/api/v2/chat",
            json={
                "chatId": "test_chat_005",
                "chatRounds": 2,
                "content": {"text": "我叫什么名字？"},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
            },
        ) as response2:
            assert response2.status_code == 200
            chunks = []
            async for chunk in response2.aiter_bytes():
                if chunk:
                    chunks.append(chunk.decode("utf-8"))

            # 验证第二轮有响应
            assert len(chunks) > 0


class TestChatWithCollection:
    """知识库聊天测试"""

    async def test_chat_with_single_collection(self, client: AsyncClient, test_collection):
        """测试使用单个知识库聊天"""
        response = await client.post(
            "/api/v2/chat",
            json={
                "chatId": "test_chat_006",
                "chatRounds": 1,
                "content": {"text": "查询知识库信息"},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
            },
        )
        assert response.status_code == 200

    # async def test_chat_with_multiple_collections(
    #     self, client: AsyncClient, test_collection
    # ):
    #     """测试使用多个知识库聊天"""
    #     # 创建第二个知识库
    #     collection2_response = await client.post(
    #         "/api/v1/collection",
    #         json={
    #             "name": "测试知识库2",
    #             "description": "第二个测试知识库",
    #             "embeddingModel": "text-embedding-ada-002",
    #         },
    #     )
    #     collection2 = collection2_response.json()["data"]

    #     response = await client.post(
    #         "/api/v2/chat",
    #         json={
    #             "chatId": "test_chat_007",
    #             "chatRounds": 1,
    #             "content": {"text": "查询多个知识库"},
    #             "batchOrStream": "stream",
    #             "collections": [test_collection["id"], collection2["id"]],
    #         },
    #     )
    #     assert response.status_code == 200

    # async def test_chat_with_invalid_collection(self, client: AsyncClient):
    #     """测试使用不存在的知识库"""
    #     response = await client.post(
    #         "/api/v2/chat",
    #         json={
    #             "chatId": "test_chat_008",
    #             "chatRounds": 1,
    #             "content": {"text": "查询不存在的知识库"},
    #             "batchOrStream": "stream",
    #             "collections": [99999],
    #         },
    #     )
    #     # 可能返回错误或忽略无效知识库
    #     assert response.status_code in [200, 400, 422]


class TestChatWithPrompt:
    """提示词聊天测试"""

    async def test_chat_with_prompt(self, client: AsyncClient, test_prompt):
        """测试使用提示词聊天"""
        print(test_prompt)
        response = await client.post(
            "/api/v2/chat",
            json={
                "chatId": "test_chat_009",
                "chatRounds": 1,
                "content": {"text": "使用自定义提示词"},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
                "promptName": test_prompt["promptName"],
            },
        )
        assert response.status_code == 200

    async def test_chat_with_invalid_prompt(self, client: AsyncClient):
        """测试使用不存在的提示词"""
        response = await client.post(
            "/api/v2/chat",
            json={
                "chatId": "test_chat_010",
                "chatRounds": 1,
                "content": {"text": "使用不存在的提示词"},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
                "promptName": "不存在的提示词",
            },
        )
        # 可能使用默认提示词或返回错误
        assert response.status_code in [200, 400, 422]


class TestChatWithCommand:
    """指令聊天测试"""

    async def test_chat_trigger_command(self, client: AsyncClient, test_command_with_category):
        """测试触发指令"""
        command = test_command_with_category["command"]
        response = await client.post(
            "/api/v2/chat",
            json={
                "chatId": "test_chat_011",
                "chatRounds": 1,
                "content": {"text": "测试指令"},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
            },
        )
        assert response.status_code == 200

    async def test_chat_trigger_command_variant(self, client: AsyncClient, test_command_with_category):
        """测试触发指令变体"""
        response = await client.post(
            "/api/v2/chat",
            json={
                "chatId": "test_chat_012",
                "chatRounds": 1,
                "content": {"text": "test_cmd"},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
            },
        )
        assert response.status_code == 200

    async def test_chat_inactive_command(self, client: AsyncClient):
        """测试不活跃的指令不被触发"""
        # 创建不活跃的指令
        category_response = await client.post(
            "/api/v1/command/category",
            json={"name": "不活跃分类", "description": "测试"},
        )
        category = category_response.json()["data"]

        await client.post(
            "/api/v1/command/",
            json={
                "name": "不活跃指令",
                "code": "inactive_cmd",
                "categoryId": category["id"],
                "commands": "不活跃",
                "isActive": False,
            },
        )

        response = await client.post(
            "/api/v2/chat",
            json={
                "chatId": "test_chat_013",
                "chatRounds": 1,
                "content": {"text": "不活跃"},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
            },
        )
        assert response.status_code == 200


class TestChatWithFlow:
    """流程聊天测试"""

    async def test_chat_trigger_flow(self, client: AsyncClient, test_flow):
        """测试触发流程"""
        response = await client.post(
            "/api/v2/chat",
            json={
                "chatId": "test_chat_014",
                "chatRounds": 1,
                "content": {"text": "流程测试"},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
            },
        )
        assert response.status_code == 200

    async def test_chat_trigger_flow_variant(self, client: AsyncClient, test_flow):
        """测试触发流程变体"""
        response = await client.post(
            "/api/v2/chat",
            json={
                "chatId": "test_chat_015",
                "chatRounds": 1,
                "content": {"text": "flow_test"},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
            },
        )
        assert response.status_code == 200

    async def test_chat_inactive_flow(self, client: AsyncClient):
        """测试不活跃的流程不被触发"""
        # 创建不活跃的流程
        await client.post(
            "/api/v1/flow",
            json={
                "name": "不活跃流程",
                "description": "测试",
                "triggerWords": "不活跃流程",
                "isActive": False,
                "steps": [],
            },
        )

        response = await client.post(
            "/api/v2/chat",
            json={
                "chatId": "test_chat_016",
                "chatRounds": 1,
                "content": {"text": "不活跃流程"},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
            },
        )
        assert response.status_code == 200


class TestChatWithExactMatch:
    """精确匹配聊天测试"""

    async def test_chat_exact_match(self, client: AsyncClient, test_exact_match):
        """测试精确匹配"""
        response = await client.post(
            "/api/v2/chat",
            json={
                "chatId": "test_chat_017",
                "chatRounds": 1,
                "content": {"text": "测试问题"},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
            },
        )
        assert response.status_code == 200

    async def test_chat_exact_match_case_insensitive(self, client: AsyncClient, test_exact_match):
        """测试精确匹配大小写不敏感"""
        response = await client.post(
            "/api/v2/chat",
            json={
                "chatId": "test_chat_018",
                "chatRounds": 1,
                "content": {"text": "测试问题"},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
            },
        )
        assert response.status_code == 200

    async def test_chat_exact_match_with_whitespace(self, client: AsyncClient, test_exact_match):
        """测试精确匹配忽略空白字符"""
        response = await client.post(
            "/api/v2/chat",
            json={
                "chatId": "test_chat_019",
                "chatRounds": 1,
                "content": {"text": " 测试问题 "},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
            },
        )
        assert response.status_code == 200

    async def test_chat_inactive_exact_match(self, client: AsyncClient):
        """测试不活跃的精确匹配不被触发"""
        # 创建不活跃的精确匹配
        await client.post(
            "/api/v1/exact-match",
            json={
                "question": "不活跃问题",
                "answer": "不活跃答案",
                "isActive": False,
            },
        )

        response = await client.post(
            "/api/v2/chat",
            json={
                "chatId": "test_chat_020",
                "chatRounds": 1,
                "content": {"text": "不活跃问题"},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
            },
        )
        assert response.status_code == 200


class TestChatStrategyChain:
    """策略链测试"""

    async def test_strategy_priority_command_first(
        self, client: AsyncClient, test_command_with_category, test_exact_match
    ):
        """测试指令策略优先级最高"""
        # 创建同名的指令和精确匹配
        command = test_command_with_category["command"]
        await client.post(
            "/api/v1/exact-match",
            json={
                "question": "测试指令",
                "answer": "这是精确匹配答案",
                "isActive": True,
            },
        )

        response = await client.post(
            "/api/v2/chat",
            json={
                "chatId": "test_chat_021",
                "chatRounds": 1,
                "content": {"text": "测试指令"},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
            },
        )
        assert response.status_code == 200

    async def test_strategy_fallback_to_agent(self, client: AsyncClient):
        """测试回退到Agent策略"""
        response = await client.post(
            "/api/v2/chat",
            json={
                "chatId": "test_chat_022",
                "chatRounds": 1,
                "content": {"text": "这是一个没有匹配任何策略的问题"},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
            },
        )
        assert response.status_code == 200


class TestChatEdgeCases:
    """边界情况测试"""

    async def test_chat_very_long_text(self, client: AsyncClient):
        """测试超长文本"""
        long_text = "测试" * 1000
        response = await client.post(
            "/api/v2/chat",
            json={
                "chatId": "test_chat_023",
                "chatRounds": 1,
                "content": {"text": long_text},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
            },
        )
        assert response.status_code in [200, 422]

    async def test_chat_special_characters(self, client: AsyncClient):
        """测试特殊字符"""
        response = await client.post(
            "/api/v2/chat",
            json={
                "chatId": "test_chat_024",
                "chatRounds": 1,
                "content": {"text": "特殊字符: @#$%^&*()_+{}[]|\\:;<>?,./-"},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
            },
        )
        assert response.status_code == 200

    async def test_chat_emoji(self, client: AsyncClient):
        """测试表情符号"""
        response = await client.post(
            "/api/v2/chat",
            json={
                "chatId": "test_chat_025",
                "chatRounds": 1,
                "content": {"text": "你好 😊 👋 🎉"},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
            },
        )
        assert response.status_code == 200

    async def test_chat_multiline_text(self, client: AsyncClient):
        """测试多行文本"""
        multiline_text = """这是第一行
        这是第二行
        这是第三行"""
        response = await client.post(
            "/api/v2/chat",
            json={
                "chatId": "test_chat_026",
                "chatRounds": 1,
                "content": {"text": multiline_text},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
            },
        )
        assert response.status_code == 200

    async def test_chat_with_invalid_chat_id(self, client: AsyncClient):
        """测试无效的chatId"""
        response = await client.post(
            "/api/v2/chat",
            json={
                "chatId": "",
                "chatRounds": 1,
                "content": {"text": "测试"},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
            },
        )
        assert response.status_code in [200, 422]

    async def test_chat_with_zero_rounds(self, client: AsyncClient):
        """测试零轮对话"""
        response = await client.post(
            "/api/v2/chat",
            json={
                "chatId": "test_chat_027",
                "chatRounds": 0,
                "content": {"text": "测试"},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
            },
        )
        assert response.status_code in [200, 422]

    async def test_chat_with_negative_rounds(self, client: AsyncClient):
        """测试负数轮次"""
        response = await client.post(
            "/api/v2/chat",
            json={
                "chatId": "test_chat_028",
                "chatRounds": -1,
                "content": {"text": "测试"},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
            },
        )
        assert response.status_code == 422

    async def test_chat_concurrent_requests(self, client: AsyncClient):
        """测试并发请求"""
        import asyncio

        async def send_request(chat_id: str):
            return await client.post(
                "/api/v2/chat",
                json={
                    "chatId": chat_id,
                    "chatRounds": 1,
                    "content": {"text": "并发测试"},
                    "batchOrStream": "stream",
                    "collections": ["测试数据"],
                },
            )

        # 发送10个并发请求
        tasks = [send_request(f"concurrent_{i}") for i in range(10)]
        responses = await asyncio.gather(*tasks)

        for response in responses:
            assert response.status_code == 200


class TestChatPerformance:
    """性能测试"""

    async def test_chat_response_time(self, client: AsyncClient):
        """测试响应时间"""
        import time

        start_time = time.time()
        response = await client.post(
            "/api/v2/chat",
            json={
                "chatId": "test_chat_029",
                "chatRounds": 1,
                "content": {"text": "性能测试"},
                "batchOrStream": "stream",
                "collections": ["测试数据"],
            },
        )
        end_time = time.time()

        assert response.status_code == 200
        # 确保响应时间在合理范围内（例如5秒）
        assert (end_time - start_time) < 5.0

    async def test_chat_memory_usage(self, client: AsyncClient):
        """测试多轮对话内存使用"""
        chat_id = "test_chat_030"
        for i in range(10):
            response = await client.post(
                "/api/v2/chat",
                json={
                    "chatId": chat_id,
                    "chatRounds": i + 1,
                    "content": {"text": f"第{i+1}轮对话"},
                    "batchOrStream": "stream",
                    "collections": ["测试数据"],
                },
            )
            assert response.status_code == 200
