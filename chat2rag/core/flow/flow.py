import uuid
from typing import Generator

from cachetools import TTLCache
from openai import OpenAI

from chat2rag.config import CONFIG
from chat2rag.database.connection import db_session
from chat2rag.database.models import FlowData
from chat2rag.database.services.flow_service import FlowDataService

client = OpenAI(
    api_key=CONFIG.OPENAI_API_KEY,
    base_url=CONFIG.OPENAI_BASE_URL,
)

# 初始化服务
flow_service = FlowDataService(FlowData)

# 流程定义
with db_session() as db:
    FLOWS = flow_service.get_flows_structure(db)
    print(FLOWS)

# FLOWS = [
#     {
#         "name": "点菜流程",
#         "desc": "当用户需要点菜时，进行询问用户想吃什么、何时送达，并确认订单",
#         "states": ["init", "ask_time", "confirm", "complete", "quit"],
#         "config": {
#             "init": {
#                 "response": "欢迎光临麦当劳。",
#                 "emoji": "微笑",
#                 "action": "挥手",
#                 "conditions": [{"trigger": "auto", "next_state": "ask_food"}],
#             },
#             "ask_food": {
#                 "response": "你想吃点什么呢？",
#                 "conditions": [{"trigger": "获取到菜品", "next_state": "ask_time"}],
#             },
#             "ask_time": {
#                 "response": "好的，你想什么时候送到？",
#                 "conditions": [{"trigger": "获取到时间", "next_state": "confirm"}],
#             },
#             "confirm": {
#                 "response": "确认下单吗？",
#                 "conditions": [
#                     {"trigger": "确认是", "next_state": "complete"},
#                     {"trigger": "确认否", "next_state": "init"},
#                 ],
#             },
#             "complete": {
#                 "response": "好的，订单已创建，马上为你准备！",
#                 "conditions": [{"trigger": "auto", "next_state": "quit"}],
#             },
#             "quit": {"response": "如果您还需要什么，请随时跟我说！"},
#         },
#     }
# ]

# 使用 TTLCache 缓存用户状态，3分钟超时
user_states = TTLCache(maxsize=100, ttl=180)


def detect_flow(query):
    """调用 LLM 判断用户是否想进入某个流程"""

    flows_string = ""
    # [f"name: {p['name']}, desc: {p['desc']}" for p in FLOWS]
    for i, flow in enumerate(FLOWS):
        flows_string += f"{i+1}. {flow['name']}。描述:{flow['desc']}\n"
    response = client.chat.completions.create(
        model="Qwen/Qwen2.5-32B-Instruct",
        messages=[
            {
                "role": "system",
                "content": f"""
根据用户问题及流程名称、描述，判断用户是否符合以下流程。
可选流程：{flows_string}
若符合则输出名称；否则返回 None。
""",
            },
            {"role": "user", "content": f"用户问题:{query}"},
        ],
        max_tokens=10,
        temperature=0.0,
        extra_body={"enable_thinking": False},
    )
    proc = response.choices[0].message.content.strip()
    return proc if proc in [p["name"] for p in FLOWS] else None


def detect_state(query: str, current_state: str, state_config: list) -> str:
    conditions = state_config.get("conditions", "")
    if not conditions:
        return None

    prompt = f"""
        用户说：{query}
        当前状态：{current_state}
        跳转配置：{conditions}
        如果用户取消，则输出 quit
        符合条件则输出下个状态，不要解释。如果无法判断，返回 None。
        """
    valid_states = [c.get("next_state") for c in conditions]
    try:
        response = client.chat.completions.create(
            model="Qwen/Qwen2.5-32B-Instruct",
            messages=[
                {
                    "role": "system",
                    "content": "你是状态机意图分类器，输出标准化 intent。",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=20,
            temperature=0.0,
            extra_body={"enable_thinking": False},
        )
        reply = response.choices[0].message.content.strip()
        print(f"状态: {reply}")
        return reply if reply in [*valid_states, "quit"] else None

    except:
        return None


def get_flow_by_name(name):
    for p in FLOWS:
        if p["name"] == name:
            return p
    return None


# 判断是否自动转移
def state_autotrans_reply(config: dict, user_id: str) -> Generator[tuple, any, any]:
    try:
        while True:
            state = user_states[user_id]["state"]
            state_node = config.get(state, {})
            condition = state_node.get("conditions")[0]
            if condition["trigger"] == "auto":
                # 更新状态
                next_state = condition["next_state"]
                user_states[user_id]["state"] = next_state
                next_state_node = config.get(next_state, {})
                for eal_response in handle_EAL(next_state_node):
                    yield eal_response

                yield next_state_node.get("response")
            else:
                break
    except Exception:
        return


# 表情、动作、链接
def handle_EAL(state_node: dict):
    """
    Handle responses to expressions, actions, and links
    """
    emoji = state_node.get("emoji", "")
    if emoji:
        yield f"[EMOJI:{emoji}]"
    action = state_node.get("action", "")
    if action:
        yield f"[ACTION:{action}]"
    link = state_node.get("link", "")
    if link:
        yield f"[LINK:{link}]"
    return


def __handle_reponse(state_config: dict, user_id: str):
    """
    发生状态转移时，处理回复内容的函数
    """
    current_state = user_states[user_id]["state"]
    state_node = state_config.get(current_state, {})

    # 表情、动作、链接
    for eal_response in handle_EAL(state_node):
        yield eal_response

    # 默认回复
    yield state_node.get("response", "")

    # 自动转移时的回复
    for reponse in state_autotrans_reply(config=state_config, user_id=user_id):
        yield reponse


def handle_user_input(user_id: str, query: str):
    state_info = user_states.get(user_id)

    # 1. 无流程状态 → 初始化流程
    if not state_info:
        proc_name = detect_flow(query)
        if not proc_name:
            return None

        flow = get_flow_by_name(proc_name)
        current_state = "init"
        next_state = current_state
        user_states[user_id] = {
            "flow": flow,
            "state": current_state,
        }
        for res in __handle_reponse(state_config=flow["config"], user_id=user_id):
            yield res

        return

    # 2. 有流程状态 → 判断是否发生状态转移
    state_info = user_states.get(user_id)
    flow = state_info["flow"]
    current_state = state_info["state"]
    state_config = flow["config"][current_state]

    # 判断是否变更
    next_state = detect_state(query, current_state, state_config)
    user_states[user_id]["state"] = next_state

    if not next_state or next_state == current_state:
        return None
    else:
        for res in __handle_reponse(state_config=flow["config"], user_id=user_id):
            yield res
        state_info = user_states.get(user_id)

    # 如果是 quit，清除状态
    if user_states.get(user_id)["state"] == "quit":
        user_states.pop(user_id, None)
        return


# 示例用法
if __name__ == "__main__":
    user_id = str(uuid.uuid4())
    print("🍽️ 欢迎使用智能点餐助手！输入 'quit' 退出。")
    while True:

        query = input("\nYou: ").strip()
        if query.lower() == "quit":
            print("Bye!")
            break
        for answer in handle_user_input(user_id, query):
            # print(f"当前状态{user_states[user_id]}")
            print(f"Bot: {answer}")
