import streamlit as st
from utils.initialize import initialize_page
from utils.sidebar import render_sidebar


@st.dialog("提示词管理", width="small")
def prompt_manage(id):
    """提示词对话框"""
    if id == "new":
        name = st.text_input("助手名称", "")
        description = st.text_input("描述", "")
        prompt = st.text_area("提示词", height=200)
    else:
        for prompt in st.session_state.prompt_list:
            if prompt["id"] == id:
                name = st.text_input("助手名称", prompt["promptName"])
                # description = st.text_input("描述", value=prompt["description"])
                prompt = st.text_area("提示词", value=prompt["promptText"], height=200)

    if st.button("保存", use_container_width=True, key="assistant_save"):
        # CallBackFunction.assistant_save(assistant_id, name, description, prompt)
        st.rerun()
    if st.button(
        "删除", use_container_width=True, type="primary", key="assistant_delete"
    ):
        # CallBackFunction.assistant_delete(assistant_id)
        st.rerun()


def prompt_page():
    row = st.columns(3) * (len(st.session_state.prompt_list) // 3 + 1)
    for i, col in enumerate(row):
        if i < len(st.session_state.prompt_list):
            with col.container(height=190):
                st.markdown(f'#### {st.session_state.prompt_list[i]["promptName"]}')
                # st.write(st.session_state.prompt_list[i]["promptText"])
                st.button(
                    "查看",
                    use_container_width=True,
                    key=f"prompt_manage{col}",
                    on_click=prompt_manage,
                    args=(st.session_state.prompt_list[i]["id"],),
                )
    st.button(
        "添加助手",
        use_container_width=True,
        type="primary",
        key=f"prompt_edit{col}",
        on_click=prompt_manage,
        args=("new",),
    )


def main():
    """
    知识库管理页面
    """
    st.title(":material/face: 提示词管理")
    initialize_page()
    render_sidebar()
    prompt_page()
    # st.markdown(st.session_state.prompt_list)


main()
