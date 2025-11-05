import asyncio
import uuid
from typing import List, Optional

from cachetools import TTLCache

from chat2rag.core.init_app import modify_db
from chat2rag.dataclass.flow_node import Node
from chat2rag.logger import get_logger
from chat2rag.models import FlowData
from chat2rag.services.flow_service import FlowDataService
from chat2rag.utils.flow_json_parse import dict_to_flow_nodes
from chat2rag.utils.llm_client import LLMClient


class UserFlowState:
    """用户流程状态"""

    def __init__(self, flow: FlowData, current_state: str = "start"):
        self.flow = flow
        self.current_state = current_state
        self.flow_nodes = dict_to_flow_nodes(flow.flow_json)


logger = get_logger(__name__)
flow_service = FlowDataService()
user_states: TTLCache = TTLCache(maxsize=100, ttl=180)  # 用户状态缓存（TTL: 3分钟）
llm_client = LLMClient()


async def match_flow_by_query(query: str, flows: list[FlowData]) -> Optional[str]:
    """根据用户查询匹配合适的流程"""
    if not flows:
        return None

    flow_names = {flow.name for flow in flows}
    flows_description = "\n".join(
        [f"{idx + 1}. {flow.name} - {flow.desc}" for idx, flow in enumerate(flows)]
    )

    system_prompt = f"""
你是流程匹配助手。根据用户问题判断是否符合以下流程：
{flows_description}
规则：
1. 如果用户问题明确匹配某个流程，返回该流程名称
2. 如果不匹配任何流程，返回 None
3. 只返回流程名称，不要其他内容
"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]

    try:
        matched_flow = await llm_client.acall_llm(messages)
        return matched_flow if matched_flow in flow_names else None
    except Exception as e:
        logger.error(f"LLM flow matching failed: {e}")
        return None


async def match_state_by_query(query: str, current_node: Node) -> Optional[str]:
    """根据用户输入和当前节点的条件，匹配状态"""
    conditions = current_node.conditions

    if not conditions:
        return None

    available_node_names = [con.transition_node_state_name for con in conditions]
    # 构建条件描述
    conditions_text = "\n".join(
        [
            f"- 如果满足：{cond.trigger}，则输出状态名:{cond.transition_node_state_name}"
            for cond in conditions
        ]
    )

    system_prompt = f"""
你是状态转移判断器。根据用户输入判断是否满足状态转移条件。
当前状态：{current_node.state_name}
转移条件：
{conditions_text}

规则：
1. 如果用户输入满足转移条件，则输出对应 状态名
2. 如果用户明确表达取消/退出，输出 'quit'
3. 否则输出 'None'"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]

    try:
        result = await llm_client.acall_llm(messages)
        return result if result in [*available_node_names, "quit", "None"] else None
    except Exception as e:
        logger.error(f"State transition determination failed: {e}")
        return None


def _handle_state_response(
    flow_nodes: List[Node], state_name: str, user_id: str, _flags: dict = None
) -> list[str]:
    """处理状态节点的响应，包括自动转移（返回所有响应列表）"""
    if _flags is None:
        _flags = {"emoji_found": False, "action_found": False}

    responses = []
    current_node: Node = next(
        (n for n in flow_nodes if n.state_name == state_name), None
    )

    if not current_node:
        logger.warning(f"State '{state_name}' not found in flow")
        return responses

    if current_node.response:
        responses.append(current_node.response)

    if current_node.emoji and not _flags["emoji_found"]:
        responses.append(f"[EMOJI: {current_node.emoji}]")
        _flags["emoji_found"] = True

    if current_node.action and not _flags["action_found"]:
        responses.append(f"[ACTION: {current_node.action}]")
        _flags["action_found"] = True

    # 处理 end 节点
    if current_node.state_name == "end":
        responses.append("已退出流程")
        user_states.pop(user_id, None)
        logger.info(f"User {user_id} exiting flow")
        return responses

    # 处理自动转移
    if current_node.is_auto:
        next_node_id = current_node.conditions[0].transition_node_id
        next_node = next((n for n in flow_nodes if n.id == next_node_id), None)

        logger.info(f"Auto transition: {state_name} -> {next_node.state_name}")
        if user_id in user_states:
            user_states[user_id].current_state = next_node.state_name

            # 递归收集下一个节点的响应
            responses.extend(
                _handle_state_response(
                    flow_nodes, next_node.state_name, user_id, _flags
                )
            )

    logger.debug("".join(responses))

    return responses


# fmt: off
async def handle_flow(user_id: str, query: str):
    """处理用户流程交互"""
    flow_state = user_states.get(user_id)
    
    # 场景1: 用户未在任何流程中，尝试匹配并初始化流程
    if not flow_state:
        _, available_flows = await flow_service.get_list(1, 999)
        target_flow_name = await match_flow_by_query(query, available_flows)
        if not target_flow_name:
            logger.info(f"No matching flow for user {user_id}")
            return
    
        logger.info(f"User {user_id} entering flow: {target_flow_name}")
        flow = await flow_service.get_flow_by_name(target_flow_name)
        if not flow:
            logger.error(f"Flow '{target_flow_name}' not found")

        # 用户状态初始化
        user_states[user_id] = UserFlowState(flow, "start")
        responses = _handle_state_response(user_states[user_id].flow_nodes, "start", user_id)

        for response in responses:
            yield response
        return

    # 场景2: 用户在流程中，处理状态转移
    current_node: Node = next(n for n in flow_state.flow_nodes if n.state_name == flow_state.current_state)
    if not current_node:
        logger.error(f"Current state node not found: {flow_state.current_state}")
        return
    
    transition_result = await match_state_by_query(query, current_node)
    if not transition_result or transition_result == "None":
        logger.info(f"No state transition for user {user_id}")
        return

    if transition_result == "quit":
        logger.info(f"User {user_id} exiting flow")
        user_states.pop(user_id, None)
        yield "已退出流程"
        return

    user_states[user_id].current_state = transition_result
    responses = _handle_state_response(user_states[user_id].flow_nodes, transition_result, user_id)
    for response in responses:
        yield response
    return
# fmt: on


# 示例用法
async def example_usage():
    """示例：如何使用流程处理器"""
    await modify_db()
    user_id = str(uuid.uuid4())

    print("🤖 智能流程助手启动！输入 'quit' 退出。\n")

    while True:
        query = input("You: ").strip()

        if query.lower() == "quit":
            print("👋 再见！")
            break

        async for response in handle_flow(user_id, query):
            print(f"Bot: {response}")

        # 显示当前状态（调试用）
        if user_id in user_states:
            state = user_states[user_id]
            print(f"[当前流程: {state.flow.name}, 状态: {state.current_state}]")


if __name__ == "__main__":
    asyncio.run(example_usage())
