import streamlit as st
from utils.initialize import initilize_messages


def render_sidebar(clear_message: bool = False, show_only: str | None = None):
    with st.sidebar:
        if show_only is None or show_only == "model_select":
            st.selectbox(
                "请选择模型",
                options=st.session_state["model_list"],
                index=st.session_state.get("model_select_index", 0),
                key="model_select",
                on_change=lambda: st.session_state.update(
                    {
                        "model_select_index": st.session_state["model_list"].index(
                            st.session_state["model_select"]
                        )
                    }
                ),
            )

        if show_only is None or show_only == "prompt_select":
            st.selectbox(
                "请选择提示词",
                options=st.session_state["prompt_name_list"],
                index=st.session_state.get("prompt_select_index", 0),
                key="prompt_select",
                on_change=lambda: st.session_state.update(
                    {
                        "prompt_select_index": st.session_state[
                            "prompt_name_list"
                        ].index(st.session_state["prompt_select"])
                    }
                ),
            )

        if show_only is None or show_only == "collection_select":
            st.selectbox(
                "请选择知识库",
                options=st.session_state["collections_list"],
                index=st.session_state.get("collection_select_index", 0),
                key="collection_select",
                on_change=lambda: st.session_state.update(
                    {
                        "collection_select_index": st.session_state[
                            "collections_list"
                        ].index(st.session_state["collection_select"])
                    }
                ),
            )

        if show_only is None or show_only == "threshold":
            st.number_input(
                "请选择阈值(精准模式下为0.88)",
                min_value=0.00,
                max_value=1.00,
                step=0.01,
                value=st.session_state.get("threshold_value", 0.60),
                key="threshold",
                on_change=lambda: st.session_state.update(
                    {"threshold_value": st.session_state["threshold"]}
                ),
            )

        if show_only is None or show_only == "topK":
            st.number_input(
                "请选择知识库返回数量",
                min_value=1,
                max_value=20,
                step=1,
                value=st.session_state.get("topK_value", 5),
                key="topK",
                on_change=lambda: st.session_state.update(
                    {"topK_value": st.session_state["topK"]}
                ),
            )

        # st.multiselect(
        #     "请选择工具",
        #     key="tool_select",
        #     options=st.session_state["tools_list"],
        #     placeholder="请选择工具",
        # )

        if show_only is None or show_only == "precision_mode":
            _, col2, _ = st.columns([2, 8, 1])
            with col2:
                st.toggle(
                    label="精准模式",
                    value=st.session_state.get("precision_mode_value", False),
                    key="precision_mode",
                    on_change=lambda: st.session_state.update(
                        {"precision_mode_value": st.session_state["precision_mode"]}
                    ),
                    width="stretch",
                )
        if clear_message:
            _, col2, _ = st.columns([1, 8, 1])
            with col2:
                st.button(
                    "清除会话",
                    key="clear_message",
                    type="primary",
                    on_click=initilize_messages,
                    use_container_width=True,
                )
