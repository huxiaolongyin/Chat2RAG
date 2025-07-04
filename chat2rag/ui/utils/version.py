import streamlit as st


def version_list():
    st.subheader("版本更新")
    with st.expander("V0.2.1 (2025-07-04)", expanded=True):
        content = """
    ### 🚀 New Features
    - 新增 Agent管道，融合MCP、RAG、ToolInvoke
    - 新增 Agent管道示例
    - 新增 MCP中streamable模式的支持
    - 新增 使用 SerperDevWebSearch进行网页搜索的功能
    - 优化 Agent Pipeline，支持 ToolCall 和 ToolResult 流式输出
    - 新增 MCP工具名的映射，使用AI对工具描述进行取名
    - 新增 streamlit ui 上增加工具选择、网络搜索、优化模型选择
    ### 🐛 Bug Fixed
    - 移除 get_bazi_info 工具，直接`+`似乎有问题
    ### 🎄 Changed
    - 修改 Base Pipeline，加入泛型变量，支持更多类型的 Pipeline
    - 增强工具管理， 并修改 tool 接口
    - 修改 Function Pipeline(将弃用)，添加 Funciton 示例
    - 修改 RAG Pipeline(将弃用)，添加 RAG 示例
    - 修改 api/v1/chat 接口，使用Agent 管道进行输出内容
    - 优化 短记忆 chat_history 内容，将 ChatMessage 集成到一个函数内
    ### 🪓 Removed
    - 移除 内置的天气服务，使用高德 MCP 代替
    - 移除 内置的微博检索工具
    - 移除 yml管理工具集
"""
        st.markdown(content)
    with st.expander("V0.2.0 (2025-06-25)", expanded=False):
        content = """
    ### 🚀 New Features
    - 新增 ASR 的服务(暂未全部接入)
    - 新增 TTS 的服务(暂未全部接入)
    - 在 prompt 中添加基础信息：时间、vin、地点
    - 新增 汉特云内部mcp服务
    - 新增 tool v2 接口，进行 MCP 和 api tool 的增删改查.
    - 新增 对多个 MCP 服务的处理，增加单例模式进行MCP的连接
    - 支持 多个知识库的检索
    - 新增 makefile 文件启动 后端和前端
    ### 🐛 Bug Fixed
    - 修复 qdrant-haystack 升级到 9.2.0，导致 qdrant.py 无法使用的问题
    - 修复 chat 接口修改导致的 collection 参数问题
    ### 🎄 Changed
    - 将 frontend、rag_core、backend 整合到chat2rag中
    - 将天气查询改为高德 MCP
    - 更新 document 从 str -> DocumentType 类型
    - 将管道的 warmup() 改到 base 中
    - 更新 haystack 和相关依赖
    - 优化冗余的配置文件，统一到 config.py 中
"""
        st.markdown(content)
    with st.expander("V0.1.2rc2 (2025-03-04)", expanded=False):
        content = """
    ### 🚀 New Features
    - 接口中添加 ASCII 标题
    - 将代码中配置里的内容提取到 env 和 config 文件中
    ### 🐛 Bug Fixe
    - 修复精准模式下，文档检索不正确的问题
    - 修复批处理下，符号分词不正确的情况
"""
        st.markdown(content)
    with st.expander("V0.1.2rc1 (2025-02-20)", expanded=False):
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
