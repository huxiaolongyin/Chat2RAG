import random

import streamlit as st
from controller.knowledge_controller import knowledge_controller
from controller.model_controller import model_controller
from controller.prompt_controller import prompt_controller
from controller.tool_controller import tool_controller
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
                if st.button("我知道了", use_container_width=True):
                    cookies["show_welcome"] = "False"
                    cookies.save()
                    st.rerun()

        welcome_page()


def initialize_page():
    """
    初始化知识库列表
    """
    # 模型
    if "model_list" not in st.session_state:
        st.session_state.model_list = model_controller.get_model_list()

    if "model_select_index" not in st.session_state:
        try:
            model_index = st.session_state.model_list.index("Qwen2.5-72B")
        except:
            print("Qwen2.5-72B 不在模型列表中")
            model_index = 0
        st.session_state.model_select_index = model_index
        st.session_state.model_select = st.session_state.model_list[model_index]

    # 知识库
    if "collections_list" not in st.session_state:
        st.session_state.collections_list = knowledge_controller.get_collection_list()

    if "collection_select_index" not in st.session_state:
        st.session_state.collection_select_index = 0
        st.session_state.collection_select = st.session_state.collections_list[0]

    # 工具
    if "tools_list" not in st.session_state:
        st.session_state.tools_list = list(tool_controller.tools.keys())

    if "tool_select_state" not in st.session_state:
        st.session_state.tool_select_state = [
            "汉特云点位导航助手",
            "城市天气查询工具",
        ]

    # 提示词
    if "prompt_list" not in st.session_state:
        st.session_state.prompt_list = prompt_controller.get_prompt_list()
    if "prompt_name_list" not in st.session_state:
        st.session_state.prompt_name_list = prompt_controller.get_prompt_name_list()
    if "prompt_select_index" not in st.session_state:
        try:
            prompt_index = st.session_state.prompt_name_list.index("默认")
        except ValueError:
            print("默认 不在 prompt 列表中")
            prompt_index = 0
        st.session_state.prompt_select_index = prompt_index
        # st.session_state.prompt_select = st.session_state.prompt_name_list[prompt_index]

    # 如果 "messages" 不存在于会话状态中，则初始化它，用于加载历史消息
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "你好，有什么可以帮你的吗？"}
        ]
        st.session_state.message_id = random.randint(100000, 9000000)

    # 精准模式
    if "precision_mode_state" not in st.session_state:
        st.session_state.precision_mode_state = False

    # 网络搜索
    if "web_search_mode_state" not in st.session_state:
        st.session_state.web_search_mode_state = False

    # 页码
    if "current" not in st.session_state:
        st.session_state.current = 1
