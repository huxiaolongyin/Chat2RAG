import streamlit as st

st.set_page_config(
    page_title="Chat2RAG",
    layout="centered",
    page_icon="🤖",
)


pages = [
    st.Page("views/chat.py", title="ChatBot", icon=":material/forum:"),
    st.Page("views/knowledge.py", title="知识库管理", icon=":material/auto_stories:"),
]
pg = st.navigation(pages)
pg.run()
