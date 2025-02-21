import streamlit as st


def version_list():
    st.subheader("版本更新")
    with st.expander("V0.1.2rc1 (2025-02-20)", expanded=True):
        content = """
    ### ⭐️ Highlights
    - 新增选择模型的功能，增加对 deepseek-v3 的支持
    - 新增提示词切换的功能，可以切换不同的提示词，从而实现不同的对话风格
    - 新增提示词的管理功能，可以对提示词进行增删改查
    ### 🚀 New Features
    - 使用 One-api 进行统一管理大模型
    - 新增网页 title 的对正式版和测试版显示的区分
    - 优化 query 接口和 query-stream 接口的参数
    - 提取 frontend 的公共参数到配置中
    ### 🐛 Bug Fixe
    - 修复文档检索和展示不匹配的问题
    - 去除了对 embedding 服务的存活检测，后续合并到 One-api 进行统一管理
    - 优化默认显示的 prompt 和 model
    - 使用 cookie 进行管理更新内容展示弹窗，避免浏览器刷新重复弹出
"""
        st.markdown(content)
    with st.expander("V0.1.1 (2025-01-16)", expanded=False):
        content = """
    ### ⭐️ Highlights
    - 新增精准模式匹配，在精准模式下，将优先进行问题的匹配，然后再进行文档的匹配，从而提高匹配的准确性。
    - 新增知识内容的搜索功能
    - 新增知识数据导出的功能
    ### 🚀 New Features
    - 在知识写入时，拆分为问题，问题-答案，进行向量的存储
    - 在消息中新增 uuid
    - 在环境变量中进行 function 的启用
    ### 🐛 Bug Fixe
    - 修复若干 bug
    - 修复管道时间计算的问题
    - 修复不能删除没有meta的知识的问题
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
