import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict

from enums import MessageType
from haystack.dataclasses import ChatRole


@dataclass
class ChatMessage:
    """聊天消息数据类"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    role: ChatRole = ChatRole.USER
    content: str = ""
    message_type: MessageType = MessageType.MESSAGE
    tool: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
