import datetime

from haystack.components.generators.utils import print_streaming_chunk
from haystack.dataclasses import ChatMessage

from chat2rag.core.pipelines.agent import AgentPipeline

history_messages = [
    ChatMessage.from_system(
        """
# 角色与目标

你是一个名为 笨笨同学 的服务机器人。你的核心目标是为用户提供精准、便捷、友好的信息服务和功能操作。

# 上下文信息

- 机器人识别码 (VIN): `{{ vin }}`
- 当前城市: `{{ city }}`
- 当前时间: `{{ time }}`
- 所在坐标: `{{ lng }}`, `{{ lat }}`

# 核心原则

## 1. 互动风格
- 自然流畅: 始终使用自然、流畅的完整句子进行交流，语气亲切、简洁。严禁使用项目符号或编号列表。
- 主动服务: 在合适的时机，可以主动提供相关建议或提醒，提升用户体验。

## 2. 行为逻辑
- 澄清意图: 当用户意图不明确或信息不足时，必须主动反问以获取必要信息，绝不主观臆测。
- 信息来源: 回答中不得提及“根据我的资料”、“我的知识库显示”等类似字眼，要让用户感觉信息是你自身具备的能力。
- 能力边界: 如果现有工具无法满足用户请求，应直接、礼貌地告知用户当前无法完成该操作。

## 3. 工具使用
- 参数来源: 工具的所有参数都必须源自用户的明确指令或对话上下文，严禁虚构或推断任何参数值。
- 工具合并: 如果用户请求涉及同一工具，进行合并请求，一次获取多个信息
"""
    ),
    ChatMessage.from_user(
        """
问题：{{ query }}；
参考文档：
{% if documents  %}
{% for doc in documents %}
content: {{ doc.content }} score: {{ doc.score }}
{% endfor %}
{% else %}
None
{% endif %}
    """
    ),
]
pipeline = AgentPipeline(["福建省广电集团"], model="Qwen/Qwen2.5-72B-Instruct", tools=["maps_weather"])
# Qwen/Qwen2.5-32B-Instruct  /  deepseek-ai/DeepSeek-V3   /  Qwen/Qwen2.5-Coder-32B-Instruct

print(
    pipeline.run(
        # query="今年NBA总冠军是那支队伍",
        # query="从福州大学旗山校区坐公交到三坊七巷怎么走",
        # query="今天天气怎么样",
        query="民营经济提质增效、转型升级、再创优势，离不开大批创新人才，请问省教育厅是如何深化产教融合、校企合作培养创新人才的？",
        top_k=5,
        score_threshold=0.7,
        filters={"field": "meta.type", "operator": "==", "value": "qa_pair"},
        messages=history_messages,
        vin="HTYW295157A802220",
        city="福州",
        time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        streaming_callback=print_streaming_chunk,
    )
)
