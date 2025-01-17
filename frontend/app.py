import os

import streamlit as st

title = "Chat2RAG(正式版)" if os.environ.get("DEPLOY_ENV") else "Chat2RAG(测试版)"
st.set_page_config(
    page_title=title,
    layout="centered",
    page_icon="🤖",
)


pages = [
    st.Page("views/chat.py", title="ChatBot", icon=":material/forum:"),
    st.Page("views/knowledge.py", title="知识库管理", icon=":material/auto_stories:"),
    st.Page("views/version.py", title="版本更新", icon=":material/book:"),
]
pg = st.navigation(pages)
pg.run()
