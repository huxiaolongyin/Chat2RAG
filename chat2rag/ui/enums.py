from enum import Enum


class MessageType(str, Enum):
    """消息类型枚举"""

    MESSAGE = "message"
    TOOL = "tool"
    REFERENCE = "reference"
