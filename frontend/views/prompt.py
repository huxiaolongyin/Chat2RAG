import streamlit as st
from controller.prompt_controller import prompt_controller
from utils.initialize import initialize_page
from utils.sidebar import render_sidebar


@st.dialog("提示词管理", width="small")
def prompt_manage(id):
    """提示词对话框"""
    if id == "new":
        prompt_name = st.text_input("提示词名称", "")
        prompt_intro = st.text_input("简介", "")
        prompt_text = st.text_area("提示词", height=280)
        if st.button("创建", use_container_width=True, key="prompt_create"):
            prompt_controller.create_prompt(prompt_name, prompt_intro, prompt_text)
            st.session_state.prompt_list = prompt_controller.get_prompt_list()
            st.rerun()
    else:
        # 查找对应 id 的提示词；如果找不到，显示错误信息
        prompt = next((p for p in st.session_state.prompt_list if p["id"] == id), None)
        if not prompt:
            st.error("未找到提示词")
            return
        prompt_name = st.text_input("助手名称", prompt["promptName"])
        prompt_intro = st.text_input("描述", value=prompt["promptIntro"])
        prompt_text = st.text_area("提示词", value=prompt["promptText"], height=280)
        if st.button("更新", use_container_width=True, key="prompt_update"):
            prompt_controller.update_prompt(id, prompt_name, prompt_intro, prompt_text)
            st.session_state.prompt_list = prompt_controller.get_prompt_list()
            st.rerun()
        if prompt_name != "默认":
            if st.button(
                "删除",
                use_container_width=True,
                type="primary",
                key="assistant_delete",
            ):

                prompt_controller.delete_prompt(id)
                st.session_state.prompt_list = prompt_controller.get_prompt_list()
                st.rerun()


def prompt_page():
    row = st.columns(3) * (len(st.session_state.prompt_list) // 3 + 1)
    for i, col in enumerate(row):
        if i < len(st.session_state.prompt_list):
            with col.container(height=160):
                st.markdown(f'##### {st.session_state.prompt_list[i]["promptName"]}')
                st.write(st.session_state.prompt_list[i]["promptIntro"])
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


main()
