import random

import streamlit as st
from streamlit_cookie import EncryptedCookieManager
from utils.version import version_list


def init_welcome_page():
    """初始化欢迎页"""
    # 配置 Cookie 管理器
    st.markdown(
        """
    <style>
    .st-key-CookieManager-sync_cookies {
        display: none;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )
    cookies = EncryptedCookieManager(
        prefix="Chat2RAG",  # 可选，用于区分不同应用的 Cookie 前缀
        password="SUPER_SECRET_PASSWORD",  # 用于加密 Cookie 的密码，请自行替换
    )

    # 等待 Cookie 管理器初始化完成
    if not cookies.ready():
        st.stop()

    # 尝试从 Cookie 中加载状态，如果不存在则默认显示欢迎页 (True)
    if "show_welcome" not in cookies:
        cookies["show_welcome"] = "True"
        cookies.save()

    show_welcome = cookies.get("show_welcome", "True") == "True"

    if show_welcome:

        @st.dialog("欢迎", width="large")
        def welcome_page():
            st.write("👋 欢迎使用本应用！")
            st.write("这里是一些使用说明...")
            version_list()
            _, col, _ = st.columns([2, 1, 2])
            with col:
                if st.button("我知道了", width="stretch"):
                    cookies["show_welcome"] = "False"
                    cookies.save()
                    st.rerun()

        welcome_page()


def initialize_page():
    """
    初始化知识库列表
    """

    # 如果 "messages" 不存在于会话状态中，则初始化它，用于加载历史消息
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "你好，有什么可以帮你的吗？"}
        ]
        st.session_state.message_id = random.randint(100000, 9000000)

    # 页码
    if "current" not in st.session_state:
        st.session_state.current = 1
