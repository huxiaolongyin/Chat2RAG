import streamlit as st

st.set_page_config(
    page_title="Chat2RAG",
    layout="centered",
    page_icon="🤖",
)

pages = [st.Page("views/chat.py", title="ChatBot", icon=":material/forum:")]
pg = st.navigation(pages)
pg.run()
