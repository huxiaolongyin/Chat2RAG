from typing import List, Optional

from cachetools import TTLCache
from haystack.dataclasses import ChatMessage, ChatRole, ToolCall
from sqlalchemy.orm import Session

from chat2rag.database.models import Prompt
from chat2rag.logger import get_logger

logger = get_logger(__name__)

DEFAULT_QUERY_TEMPLATE = """
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
