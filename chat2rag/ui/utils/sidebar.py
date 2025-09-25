from typing import Callable

import streamlit as st
from controller.knowledge_controller import knowledge_controller
from controller.model_controller import model_controller
from controller.prompt_controller import prompt_controller
from controller.tool_controller import tool_controller


def model_selector():
    """
    模型选择器
    """
    if "model_list" not in st.session_state:
        st.session_state["model_list"] = model_controller.get_model_list()
    if "model_select_index" not in st.session_state:
        if "Qwen2.5-32B" in st.session_state["model_list"]:
            st.session_state["model_select_index"] = st.session_state[
                "model_list"
            ].index("Qwen2.5-32B")
        else:
            st.session_state["model_select_index"] = 0
    if "model_select" not in st.session_state:
        index = st.session_state["model_select_index"]
        st.session_state["model_select"] = st.session_state["model_list"][index]

    def model_change():
        st.session_state["model_select_index"] = st.session_state["model_list"].index(
            st.session_state["model_select"]
        )

    st.selectbox(
        "请选择模型",
        index=st.session_state.model_select_index,
        key="model_select",
        on_change=model_change,
        options=st.session_state["model_list"],
    )


def collections_selector(func: Callable = None, *args, **kwargs):
    """
    知识库选择器
    """

    def collection_change():
        st.session_state.collection_select_index = (
            st.session_state.collections_list.index(st.session_state.collection_select)
        )
        if func:
            st.session_state.metrics_data = func(*args, **kwargs)

    if "collections_list" not in st.session_state:
        st.session_state["collections_list"] = (
            knowledge_controller.get_collection_list()
        )

    if "collection_select_index" not in st.session_state:
        st.session_state["collection_select_index"] = 0
        st.session_state["collection_select"] = st.session_state["collections_list"][0]

    st.selectbox(
        "请选择知识库",
        index=st.session_state.collection_select_index,
        key="collection_select",
        on_change=collection_change,
        options=st.session_state.collections_list,
    )


def prompt_selector():
    """
    提示词选择器
    """

    def prompt_change():
        st.session_state.prompt_select_index = st.session_state.prompt_name_list.index(
            st.session_state.prompt_select
        )

    if "prompt_list" not in st.session_state:
        st.session_state["prompt_list"] = prompt_controller.get_prompt_list()
    if "prompt_name_list" not in st.session_state:
        st.session_state["prompt_name_list"] = prompt_controller.get_prompt_name_list()
    if "prompt_select_index" not in st.session_state:
        try:
            prompt_index = st.session_state["prompt_name_list"].index("默认")
        except ValueError:
            print("默认 不在 prompt 列表中")
            prompt_index = 0
        st.session_state["prompt_select_index"] = prompt_index

    st.selectbox(
        "请选择提示词",
        index=st.session_state["prompt_select_index"],
        key="prompt_select",
        on_change=prompt_change,
        options=st.session_state["prompt_name_list"],
    )


def tool_selector():
    def tool_change():
        st.session_state.tool_select_state = st.session_state.tool_select

    if "tools_list" not in st.session_state:
        st.session_state.tools_list = list(tool_controller.tools.keys())

    if "tool_select_state" not in st.session_state:
        st.session_state.tool_select_state = [
            "汉特云点位导航助手",
            "城市天气查询工具",
        ]
    st.multiselect(
        "请选择工具",
        default=st.session_state.tool_select_state,
        key="tool_select",
        on_change=tool_change,
        options=st.session_state.tools_list,
        placeholder="请选择工具",
    )


def web_selector():
    def update_web_search_mode():
        st.session_state.web_search_mode_state = st.session_state.web_search_mode

    if "web_search_mode_state" not in st.session_state:
        st.session_state.web_search_mode_state = False
    st.toggle(
        label="网络搜索",
        key="web_search_mode",
        value=st.session_state.web_search_mode_state,
        on_change=update_web_search_mode,
    )


def precision_selector():
    def update_precision_mode():
        st.session_state.precision_mode_state = st.session_state.precision_mode

    if "precision_mode_state" not in st.session_state:
        st.session_state.precision_mode_state = False
    st.toggle(
        label="精准模式",
        key="precision_mode",
        value=st.session_state.precision_mode_state,
        on_change=update_precision_mode,
    )


def render_sidebar(func: Callable = None, *args, **kwargs):
    with st.sidebar:
        model_selector()
        collections_selector(func, *args, **kwargs)
        prompt_selector()
        # _, col2, _ = st.columns([1, 5, 1])
        # with col2:
        #     web_selector()
        _, col2, _ = st.columns([1, 5, 1])
        with col2:
            precision_selector()

    # del_button = st.button(
    #     "删除知识库",
    #     on_click=del_knowledge_store_dialog,
    #     args=(collection,),
    #     width='stretch',
    #     type="primary",
    # )
