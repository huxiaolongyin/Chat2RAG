import re
from typing import AsyncIterator

from chat2rag.services.sensitive_service import SensitiveService

from .base import ResponseStrategy

sensitive_word_service = SensitiveService()


class SensitiveWordStrategy(ResponseStrategy):
    """机器人敏感词策略"""

    # 示例敏感词列表，实际可从request或配置动态获取

    async def can_handle(self, query: str) -> bool:
        return True

    async def execute(self, query: str) -> AsyncIterator[str]:
        sensitive_words = await sensitive_word_service.get_active_sensitive_list()
        pattern = "|".join(map(re.escape, sensitive_words))
        if sensitive_words and re.search(pattern, query):
            answer = "您的查询包含敏感词，无法处理该请求。"
            async for item in self._yield_stream(answer, "SensitiveWordFilter"):
                yield item
            return
        # 不产生任何回复，交由下个策略处理
        return
