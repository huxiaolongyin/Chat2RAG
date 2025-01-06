import random

import streamlit as st
from controller.knowledge_controller import knowledge_controller


def initialize_page():
    # 初始化知识库列表
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
