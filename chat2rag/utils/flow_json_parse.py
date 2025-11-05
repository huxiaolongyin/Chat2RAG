import asyncio
from typing import List

from chat2rag.core.init_app import modify_db
from chat2rag.dataclass.flow_node import Condition, Node


def dict_to_flow_nodes(data: dict) -> List[Node]:
    """将字典转换为 Node dataclass"""

    # 转换 Condition
    def _to_condition(cond_list: list) -> List[Condition]:
        return [
            Condition(id=cond.get("id", ""), trigger=cond.get("trigger", ""))
            for cond in cond_list
        ]

    # 转换 Node
    def _to_node(node_dict: dict) -> Node:
        data = node_dict.get("data", {})
        node_type = node_dict.get("type", "")
        state_name = data.get("stateName")

        return Node(
            id=node_dict.get("id", ""),
            node_type=node_type,
            label=data.get("label", ""),
            is_auto=data.get("isAuto", ""),
            conditions=_to_condition(data.get("conditions", [])),
            emoji=data.get("emoji", ""),
            action=data.get("action", ""),
            response=data.get("response", ""),
            state_name=state_name if state_name else node_type,
        )

    # fmt: off
    def _update_condition(edge_dict: dict, nodes: List[Node]):
        source_handle = edge_dict.get("sourceHandle")

        source_id = edge_dict.get("source")
        target_id = edge_dict.get("target")

        # 1. 使用 next() 查找源节点，未找到则返回
        source_node = next((n for n in nodes if n.id == source_id), None)
        if not source_node:
            return

        # 2. 如果节点只有一个条件，直接更新它
        if len(source_node.conditions) == 1:
            source_node.conditions[0].transition_node_id = target_id
            source_node.conditions[0].transition_node_state_name = next((n.state_name for n in nodes if n.id == target_id), "")
            return

        # 3. 否则，解析 handle id 并查找匹配的条件进行更新
        try:
            source_handle_id = int(source_handle.split("-")[1])
        except (ValueError, IndexError):
            return  # 如果 handle 格式不正确则返回

        for condition in source_node.conditions:
            if int(condition.id) == source_handle_id:
                condition.transition_node_id = target_id
                condition.transition_node_state_name = next((n.state_name for n in nodes if n.id == target_id), "")
                break  # 找到并更新后，退出循环
    # fmt: on

    # 转换主对象
    nodes = [_to_node(n) for n in data.get("nodes", [])]

    for e in data.get("edges", []):
        _update_condition(e, nodes)

    return nodes


async def test():
    from chat2rag.services.flow_service import FlowDataService

    await modify_db()
    flow_service = FlowDataService()
    flow = await flow_service.get(3)
    flow_json = flow.flow_json
    for node in dict_to_flow_nodes(flow_json):
        print(node)


if __name__ == "__main__":
    asyncio.run(test())
