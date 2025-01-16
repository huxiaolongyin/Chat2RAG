import random

import streamlit as st
from controller.knowledge_controller import knowledge_controller
from utils.version import version_list


@st.dialog("欢迎", width="large")
def welcome_page():
    st.write("👋 欢迎使用本应用！")
    st.write("这里是一些使用说明...")
    version_list()
    _, col, _ = st.columns([2, 1, 2])
    with col:
        if st.button("我知道了", use_container_width=True):
            st.session_state.show_welcome = False
            st.rerun()


def initialize_page():
    """
    初始化知识库列表
    """
    if "collections_list" not in st.session_state:
        st.session_state.collections_list = knowledge_controller.get_collections()

    # 初始化知识库选择
    if "collection_select_index" not in st.session_state:
        st.session_state.collection_select_index = 0
        st.session_state.collection_select = st.session_state.collections_list[0]

    # 如果 "messages" 不存在于会话状态中，则初始化它，用于加载历史消息
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "你好，有什么可以帮你的吗？"}
        ]
        st.session_state.message_id = random.randint(100000, 9000000)

    if "precision_mode_state" not in st.session_state:
        st.session_state.precision_mode_state = False

    #  首次进入页面的提示
    if "show_welcome" not in st.session_state:
        st.session_state.show_welcome = True
        welcome_page()
