from typing import List, Optional

from cachetools import TTLCache
from haystack.dataclasses import ChatMessage, ChatRole, ToolCall
from sqlalchemy.orm import Session

from chat2rag.database.models import Prompt
from chat2rag.logger import get_logger

logger = get_logger(__name__)
action_list = [
    "点头",
    "摇头",
    "挥手",
    "招手",
    "耸肩",
    "鼓掌",
    "站立",
    "坐下",
    "前进",
    "后退",
]
emoji_list = [
    "微笑",
    "开心",
    "难过",
    "愤怒",
    "困惑",
    "思考",
    "惊讶",
    "疲惫",
    "害羞",
    "鼓励",
]
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

请根据以上内容回答用户问题。
你可以使用以下特殊标记来表示非文本内容：
- 动作：[ACTION:动作名称]，示例: [ACTION:{action_list[0]}]，可选动作：{'、'.join(action_list)}
- 表情：[EMOJI:emoji名称]，示例: [EMOJI:{emoji_list[0]}]，可选表情：{'、'.join(emoji_list)}
- 图片: `[IMAGE:图片地址]`，以 png、jpg、jpeg、gif 结尾的链接，示例：[IMAGE:https://pic.nximg.cn/file/20200430/24969966_224422361084_2.jpg]
- 链接：`[LINK:URL]`，示例：[LINK:https://example.com]，确保 URL 完整且以 http:// 或 https:// 开头


上述标记请在文本回复前提前合理地使用，以增强交互表现力。仅输出与问题相关的标记和回答内容，避免冗余解释。
回答：
"""


def get_prompt_template(prompt_name: str, db: Session) -> Optional[str]:
    """
    Obtain the prompt template from the database
    """
    if not prompt_name:
        return None

    prompt = db.query(Prompt).filter(Prompt.prompt_name == prompt_name).first()
    if not prompt:
        logger.warning("Prompt with name '%s' not found", prompt_name)
        try:
            prompt = (
                db.query(Prompt)
                .filter(Prompt.prompt_name in ["默认", "default"])
                .first()
            )
            return prompt.prompt_text
        except Exception as e:
            logger.error("Error retrieving prompt '%s': %s", prompt_name, str(e))
            return None
    return prompt.prompt_text


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
        """
        Add a message to the cache
        """
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

    def get_history_messages(
        self,
        prompt_name: str,
        chat_id: str,
        db: Session,
        rounds: int = 1,
    ) -> List[ChatMessage]:
        """
        get the history messages from the cache
        """
        logger.info(
            "Get the history messages. Prompt name: %s; Chat ID: %s; History messages length: %d",
            prompt_name,
            chat_id,
            rounds,
        )
        prompt_template = get_prompt_template(prompt_name, db)
        history_messages = [ChatMessage.from_system(prompt_template)]
        cache_messages = self.message_cache.get(chat_id, [])
        if cache_messages:
            history_messages.extend(cache_messages[-rounds * 2 :])
        history_messages.append(ChatMessage.from_user(DEFAULT_QUERY_TEMPLATE))
        return history_messages
