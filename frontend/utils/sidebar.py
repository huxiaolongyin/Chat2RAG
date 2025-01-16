import streamlit as st


def collection_change():
    st.session_state.collection_select_index = st.session_state.collections_list.index(
        st.session_state.collection_select
    )


# 创建回调函数来更新状态
def update_precision_mode():
    st.session_state.precision_mode_state = st.session_state.precision_mode


def render_sidebar():
    with st.sidebar:
        st.selectbox(
            "请选择知识库",
            index=st.session_state.collection_select_index,
            key="collection_select",
            on_change=collection_change,
            options=st.session_state.collections_list,
        )
        _, col2, _ = st.columns([1, 5, 1])
        with col2:
            st.toggle(
                label="精准模式",
                key="precision_mode",
                value=st.session_state.precision_mode_state,
                on_change=update_precision_mode,
            )

    # del_button = st.button(
    #     "删除知识库",
    #     on_click=del_knowledge_store_dialog,
    #     args=(collection,),
    #     use_container_width=True,
    #     type="primary",
    # )
