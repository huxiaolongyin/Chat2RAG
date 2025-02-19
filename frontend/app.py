import streamlit as st
from config import CONFIG

st.set_page_config(
    page_title=CONFIG.TITLE,
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
