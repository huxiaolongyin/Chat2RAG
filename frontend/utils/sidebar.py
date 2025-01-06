import streamlit as st


def collection_change():
    st.session_state.collection_select_index = st.session_state.collections_list.index(
        st.session_state.collection_select
    )


def render_sidebar():
    with st.sidebar:
        st.selectbox(
            "请选择知识库",
            index=st.session_state.collection_select_index,
            key="collection_select",
            on_change=collection_change,
            options=st.session_state.collections_list,
        )

    # del_button = st.button(
    #     "删除知识库",
    #     on_click=del_knowledge_store_dialog,
    #     args=(collection,),
    #     use_container_width=True,
    #     type="primary",
    # )
