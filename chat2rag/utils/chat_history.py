from typing import List, Optional

from cachetools import TTLCache
from haystack.dataclasses import (
    ChatMessage,
    ChatRole,
    ImageContent,
    TextContent,
    ToolCall,
)

from chat2rag.config import CONFIG
from chat2rag.logger import get_logger
from chat2rag.schemas.prompt import PromptCreate
from chat2rag.services.action_service import RobotActionService
from chat2rag.services.expression_service import RobotExpressionService
from chat2rag.services.prompt_service import PromptService

logger = get_logger(__name__)
prompt_service = PromptService()
action_service = RobotActionService()
expression_service = RobotExpressionService()


# [
#     "点头",
#     "摇头",
#     "挥手",
#     "招手",
#     "耸肩",
#     "鼓掌",
#     "站立",
#     "坐下",
#     "前进",
#     "后退",
# ]
# emoji_list = [
#     "微笑",
#     "开心",
#     "难过",
#     "愤怒",
#     "困惑",
#     "思考",
#     "惊讶",
#     "疲惫",
#     "害羞",
#     "鼓励",
# ]
DEFAULT_QUERY_TEMPLATE = f"""
问题：{{{{ query }}}}；

参考文档：
{{% if documents  %}}
    {{% for doc in documents %}}
content: {{{{ doc.content }}}} score: {{{{ doc.score }}}}
    {{% endfor %}}
{{% else %}}
    None
{{% endif %}}
"""

EXTRA_PROMPT = """
请根据以上内容回答用户问题。
你可以使用以下特殊标记来表示非文本内容：
- 动作：[ACTION:动作名称]，示例: [ACTION:{action0}]，可选动作：可选动作：{actions}
- 表情：[EMOJI:emoji名称]，示例: [EMOJI:{emoji0}]，可选表情：可选表情：{emojis}
- 图片: `[IMAGE:图片地址]`，以 png、jpg、jpeg、gif 结尾的链接，示例：[IMAGE:https://pic.nximg.cn/file/20200430/24969966_224422361084_2.jpg]
- 链接：`[LINK:URL]`，示例：[LINK:https://example.com]，确保 URL 完整且以 http:// 或 https:// 开头


上述标记请在文本回复前提前合理地使用，以增强交互表现力。仅输出与问题相关的标记和回答内容，避免冗余解释。
回答：
"""


async def get_prompt_template(prompt_name: str) -> Optional[str]:
    """
    Obtain the prompt template from the database
    """
    if not prompt_name:
        return None
    prompt = await prompt_service.get_by_prompt_name(prompt_name)

    # 没找到提示词则使用默认或创建
    if not prompt:
        logger.warning("Prompt with name '%s' not found", prompt_name)
        try:

            prompt = await prompt_service.model.filter(
                prompt_name__in=["默认", "default"]
            ).first()
            if not prompt:
                logger.debug("Create default prompt '%s'", prompt_name)
                prompt = await prompt_service.create(
                    PromptCreate(
                        promptName="默认",
                        promptDesc=f"默认",
                        promptText=CONFIG.RAG_PROMPT_TEMPLATE,
                    )
                )
            return prompt.get("promptText")

        except Exception as e:
            logger.error("Error retrieving prompt '%s': %s", prompt_name, str(e))
            return None
    return prompt.get("promptText")


class ChatHistory:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, ttl: int = 300):
        # 使用TTLCache自动处理过期
        self.message_cache = TTLCache(maxsize=1000, ttl=ttl)

    def add_message(
        self,
        chat_id: str,
        role: Optional[ChatRole] = None,
        text: Optional[str] = None,
        tool_result: Optional[str] = None,
        tool_call: Optional[ToolCall] = None,
        messages: Optional[List[ChatMessage]] = None,
    ):
        """Add a message to the cache"""

        if chat_id not in self.message_cache:
            self.message_cache[chat_id] = []

        if messages:
            self.message_cache[chat_id].extend(messages)
        else:
            if role == ChatRole.USER:
                self.message_cache[chat_id].append(ChatMessage.from_user(text))
            elif role == ChatRole.TOOL:
                self.message_cache[chat_id].append(
                    ChatMessage.from_tool(tool_result, tool_call)
                )
            elif role == ChatRole.ASSISTANT:
                self.message_cache[chat_id].append(ChatMessage.from_assistant(text))
            else:
                raise ValueError("Invalid role")

    def get_last_n_rounds(self, cache_messages: List[ChatMessage], rounds: int):
        """
        根据user->assistant的顺序回溯最近的rounds轮对话，
        其中一轮包括user消息及紧随其后的assistant（包含中间tool）。
        返回截取的消息列表（从旧到新排好序）
        """
        if not cache_messages or rounds < 1:
            return []

        rounds_found = 0
        collected = []
        i = len(cache_messages) - 1

        # 临时堆栈，用来临时保存当前轮段消息，方便完成后整体加入结果
        temp_stack = []

        # 逆序遍历消息
        while i >= 0 and rounds_found < rounds:
            current_msg = cache_messages[i]

            temp_stack.insert(0, current_msg)  # 头插，保持顺序

            # 检查是否遇到一轮对话开始的user消息
            if current_msg.role == ChatRole.USER:

                # 找到了user消息，一个完整轮次的起点
                rounds_found += 1

                # 将这轮对话消息加入总收集列表，从前往后
                collected = temp_stack + collected
                temp_stack = []

            i -= 1

        return collected

    async def get_history_messages(
        self,
        prompt_name: str,
        chat_id: str,
        rounds: int = 1,
        collection: str = None,
        enable_extra_prompt: bool = True,
        image: str = "",
    ) -> List[ChatMessage]:
        """get the history messages from the cache"""

        logger.info(
            "Get the history messages. Prompt name: %s; Chat ID: %s; History messages length: %d",
            prompt_name,
            chat_id,
            rounds,
        )

        # Prepare system prompt with optional context about collection
        system_context = f"你当前处于{collection}场景下。\n" if collection else ""
        system_prompt = system_context + await get_prompt_template(prompt_name)
        messages = [ChatMessage.from_system(system_prompt)]

        rounds_to_retrieve = max(0, rounds - 1)  # exclude current round

        cached_msgs = self.message_cache.get(chat_id, [])
        if cached_msgs and rounds_to_retrieve > 0:
            recent_msgs = self.get_last_n_rounds(cached_msgs, rounds_to_retrieve)
            messages.extend(recent_msgs)

        user_msg = DEFAULT_QUERY_TEMPLATE
        if enable_extra_prompt:
            action_list = await action_service.get_active_action_list()
            emoji_list = await expression_service.get_active_expression_list()
            formatted_prompt = EXTRA_PROMPT.format(
                action0=action_list[0],
                actions="、".join(action_list),
                emoji0=emoji_list[0],
                emojis="、".join(emoji_list),
            )
            user_msg += formatted_prompt

        contents = [user_msg]
        if image:
            contents.append(ImageContent.from_url(image))
        messages.append(ChatMessage.from_user(content_parts=contents))
        return messages
