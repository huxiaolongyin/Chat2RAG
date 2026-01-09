"""消息管理服务"""

from typing import List

import streamlit as st
from config import CONFIG
from dataclass.chat import ChatMessage
from enums import MessageType
from haystack.dataclasses import ChatRole


class MessageService:
    """消息管理服务类"""

    @staticmethod
    def initialize_messages():
        """初始化消息列表"""
        if "messages" not in st.session_state:
            st.session_state["messages"] = []

    @staticmethod
    def add_message(
        role: ChatRole,
        content: str,
        message_type: MessageType = MessageType.MESSAGE,
        tool: str | None = None,
        **metadata,
    ) -> ChatMessage:
        """添加消息到历史记录"""

        message = ChatMessage(role=role, content=content, message_type=message_type, tool=tool, metadata=metadata)

        # 检查消息历史限制
        if len(st.session_state["messages"]) >= CONFIG.MAX_MESSAGE_HISTORY:
            # 移除最旧的消息，但保留系统消息
            messages_to_remove = []
            for i, msg in enumerate(st.session_state["messages"]):

                if msg.role != ChatRole.SYSTEM:
                    messages_to_remove.append(i)
                    if len(messages_to_remove) >= 10:  # 一次移除10条
                        break

            for i in reversed(messages_to_remove):
                st.session_state["messages"].pop(i)

        st.session_state["messages"].append(message)
        return message

    @staticmethod
    def get_messages() -> List[ChatMessage]:
        """获取所有消息"""
        return st.session_state["messages"]

    @staticmethod
    def update_last_message(content: str, message_type: MessageType = MessageType.MESSAGE):
        """更新最后一条消息的内容"""

        if st.session_state["messages"]:
            # 从后向前查找指定类型的消息
            for i in range(len(st.session_state["messages"]) - 1, -1, -1):
                msg: ChatMessage = st.session_state["messages"][i]
                if msg.message_type == message_type.value:
                    msg.content = content
                    break

    @staticmethod
    def clear_messages():
        """清空消息历史"""
        st.session_state["messages"] = []


message_service = MessageService()
