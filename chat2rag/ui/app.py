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


# 登录验证函数
def check_login(username, password):
    # 这里可以替换为数据库验证或其他认证方式
    valid_users = {"admin": "HTW@12345"}
    return valid_users.get(username) == password


# 登录界面
def login_page():
    st.title("🔐 登录")

    with st.form("login_form"):
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        submit = st.form_submit_button("登录")

        if submit:
            if check_login(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("用户名或密码错误")


# 检查登录状态
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# 根据登录状态显示不同页面
if not st.session_state.logged_in:
    login_page()
else:

    # 原有的页面导航
    pages = [
        st.Page("views/chat.py", title="ChatBot", icon=":material/forum:"),
        st.Page("views/knowledge.py", title="知识库管理", icon=":material/auto_stories:"),
        st.Page("views/prompt.py", title="提示词管理", icon=":material/face:"),
        st.Page("views/metric.py", title="指标分析", icon=":material/trending_up:"),
        st.Page("views/version.py", title="版本更新", icon=":material/book:"),
    ]
    pg = st.navigation(pages, expanded=True)
    pg.run()

    # 添加登出按钮
    with st.sidebar:
        st.write(f"欢迎, {st.session_state.username}")
        if st.button("登出", width="stretch"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.rerun()
