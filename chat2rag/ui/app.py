import streamlit as st
from config import CONFIG
from utils.initialize import initialize_session

st.set_page_config(
    page_title=CONFIG.TITLE,
    layout="centered",
    page_icon="🤖",
)

# 初始化会话
initialize_session()

pages = [
    st.Page("views/chat.py", title="ChatBot", icon=":material/forum:"),
    st.Page("views/knowledge.py", title="知识库管理", icon=":material/auto_stories:"),
    st.Page("views/prompt.py", title="提示词管理", icon=":material/face:"),
    # st.Page("views/tool.py", title="工具管理", icon=":material/apps:"),
    st.Page("views/metric.py", title="指标分析", icon=":material/trending_up:"),
    st.Page("views/version.py", title="版本更新", icon=":material/book:"),
]
pg = st.navigation(pages, expanded=True)
pg.run()
