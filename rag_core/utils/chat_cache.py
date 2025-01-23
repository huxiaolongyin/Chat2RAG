from typing import List

from cachetools import TTLCache
from haystack.dataclasses import ChatMessage


class ChatCache:
    def __init__(self, ttl: int = 300):
        # 使用TTLCache自动处理过期
        self.cache = TTLCache(maxsize=1000, ttl=ttl)

    def add_message(self, chat_id: str, content: str, role: str):
        if chat_id not in self.cache:
            self.cache[chat_id] = []
        if role == "user":
            self.cache[chat_id].append(ChatMessage.from_user(content))
        else:
            self.cache[chat_id].append(ChatMessage.from_assistant(content))

    def get_messages(self, chat_id: str, rounds: int = 1) -> List[ChatMessage]:
        messages = self.cache.get(chat_id, [])
        return messages[-rounds * 2 :] if messages else []
