import json
import os

import requests
import streamlit as st
from controller.knowledge_controller import knowledge_controller
from utils.initialize import initialize_page
from utils.sidebar import render_sidebar

# from pyinstrument import Profiler
# profiler = Profiler()
# profiler.start()

chat_container = st.container()

BACKEND_HOST = os.environ.get("BACKEND_HOST", "host.docker.internal")
BACKEND_PORT = os.environ.get("BACKEND_PORT", "8000")


def get_stream_response(query: str) -> requests.Response:
    """
    获取流式响应
    """
    return requests.get(
        f"http://{BACKEND_HOST}:{BACKEND_PORT}/api/v1/chat/query-stream",
        params={
            "collectionName": st.session_state.collection_select,
            "query": query,
            "batchOrStream": "stream",
            "chatId": st.session_state.message_id,
            "chatRounds": 5,
            "toolList": ["all"],
        },
        stream=True,
    )


def process_stream_response(response: requests.Response, placeholder):
    """
    处理流式响应
    """
    full_response = ""
    for chunk in response.iter_lines():
        if chunk:
            decoded_chunk = json.loads(chunk.decode("utf-8").replace("data: ", ""))
            if decoded_chunk.get("content"):
                full_response += decoded_chunk["content"]
                placeholder.markdown(full_response)
    return full_response


def display_chat_history():
    """
    显示聊天历史
    """
    for message in st.session_state.messages:
        # 根据消息类型使用不同的显示方式
        if message.get("type") == "reference":
            with st.chat_message("assistant"):
                with st.expander("参考文档"):
                    st.markdown(message["content"])
        else:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])


def display_references(documents: list):
    """
    在streamlit 显示文档引用
    """
    if documents:
        # 构建参考文档的markdown格式
        references_md = ""
        for doc in documents:
            references_md += (
                f"文档（相关度: {doc['score']*100:.2f}%）：{doc['content']}\n\n"
            )
        # 显示当前参考文档
        with st.expander("参考文档"):
            st.write(references_md)

        # 将参考文档添加到历史消息中
        st.session_state.messages.append(
            {
                "role": "system",
                "content": references_md,
                "type": "reference",  # 添加类型标记
            }
        )


def handle_user_input(query: str):
    """处理用户输入"""
    # 添加用户消息
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.write(query)

    # 处理助手响应
    with st.chat_message("assistant"):
        with st.spinner("生成回答中"):
            message_placeholder = st.empty()

            # 获取并处理响应
            response = get_stream_response(query)
            full_response = process_stream_response(response, message_placeholder)

            # 保存助手回复
            message_placeholder.markdown(full_response)
            st.session_state.messages.append(
                {"role": "assistant", "content": full_response}
            )

            # 获取引用文档
            documents = knowledge_controller.query_document(
                st.session_state.collection_select, query=query
            )

            display_references(documents)


def main():
    """主函数"""
    # 初始化页面
    chat_container = st.container()
    initialize_page()
    render_sidebar()

    # 显示聊天界面
    with chat_container:
        display_chat_history()

    # 处理用户输入
    if query := st.chat_input("你想说什么?"):
        handle_user_input(query)


main()
