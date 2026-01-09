"""消息渲染组件"""

from typing import List

import streamlit as st
from config import CONFIG
from dataclass.chat import ChatMessage
from enums import MessageType


class MessageRenderer:
    """消息渲染器"""

    @staticmethod
    def render_message(message: ChatMessage):
        """渲染单个消息"""
        if message.message_type == MessageType.REFERENCE:
            MessageRenderer._render_reference_message(message)
        elif message.message_type == MessageType.TOOL:
            MessageRenderer._render_tool_message(message)
        else:
            MessageRenderer._render_normal_message(message)

    @staticmethod
    def _render_normal_message(message: ChatMessage):
        """渲染普通消息"""
        with st.chat_message(message.role.value):
            st.markdown(message.content)

    @staticmethod
    def _render_reference_message(message: ChatMessage):
        """渲染参考文档消息"""
        with st.chat_message("assistant"):
            with st.expander("📒 参考文档", expanded=False):
                st.markdown(message.content)

    @staticmethod
    def _render_tool_message(message: ChatMessage):
        """渲染工具调用消息"""
        with st.chat_message("assistant"):
            tool_name = message.tool or "未知工具"
            with st.expander(f"🛠️ 工具调用: {tool_name}", expanded=False):
                st.markdown(message.content)

    @staticmethod
    def render_messages(messages: List[ChatMessage]):
        """批量渲染消息"""
        for message in messages:
            MessageRenderer.render_message(message)

    @staticmethod
    def render_references(documents: List[dict]):
        """渲染参考文档"""
        if not documents:
            return

        references_md = ""
        for doc in documents:
            score_percent = doc["score"] * 100
            references_md += (
                f"文档（相关度: {score_percent:.{CONFIG.SCORE_DISPLAY_PRECISION}f}%）：{doc['content']}\n\n"
            )

        with st.expander("📒 参考文档", expanded=False):
            st.markdown(references_md)

        return references_md


message_renderer = MessageRenderer()
