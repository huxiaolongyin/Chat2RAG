import streamlit as st


def version_list():
    st.subheader("版本更新")
    with st.expander("V0.1.1 (2025-01-16)", expanded=True):
        content = """
    ### ⭐️ Highlights
    - 新增精准模式匹配，在精准模式下，将优先进行问题的匹配，然后再进行文档的匹配，从而提高匹配的准确性。
    - 新增知识内容的搜索功能
    ### 🚀 New Features
    - 在知识写入时，拆分为问题，问题-答案，进行向量的存储
    ### 🐛 Bug Fixe
    - 修复若干 bug
"""
        st.markdown(content)
    with st.expander("V0.1.0 (2025-01-10)", expanded=False):
        content = """
    ### ⭐️ Highlights
    - 新增 RAG 流式、批式 交流 
    - 新增 函数调用功能
    - 新增 知识库的增删改查、导入导出
    - 新增 docker / docker compose 部署
"""
        st.markdown(content)
