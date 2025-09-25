import json

import requests
import streamlit as st
from controller.knowledge_controller import knowledge_controller
from utils.initialize import init_welcome_page, initialize_page
from utils.sidebar import render_sidebar

# from pyinstrument import Profiler
# profiler = Profiler()
# profiler.start()

# chat_container = st.container()


def get_stream_response(query: str) -> requests.Response:
    """
    获取流式响应
    """
    # tools: list = [tool_controller.tools.get(t) for t in st.session_state.tool_select]
    # if st.session_state.web_search_mode_state:
    #     tools = tools + ["web_search"]
    json_content = {
        "generatorModel": st.session_state.model_select,
        "promptName": st.session_state.prompt_select,
        "collectionName": st.session_state.collection_select,
        "batchOrStream": "batch",
        "precisionMode": 1 if st.session_state.precision_mode else 0,
        "query": query,
        "chatId": str(st.session_state.message_id),
        "chatRounds": 5,
        # "tools": tools,
        # "flows": ["点菜流程"],
        # "extraParams": {
        #     "vin": "HTYW684948A352077",
        #     "lat": 26.062731,
        #     "lng": 119.235434,
        #     "city": "福州",
        # },
    }
    return requests.get(
        f"http://127.0.0.1:8000/api/v1/chat/query-stream",
        params=json_content,
        stream=True,
    )


def process_stream_response(response: requests.Response, placeholder):
    """
    处理流式响应
    """
    full_response = ""
    current_tool = None
    current_tool_arguments = None

    # 添加聊天占位
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": "",
            "type": "message",  # 添加类型标记
        }
    )
    for chunk in response.iter_lines():
        if chunk:

            decoded_chunk = json.loads(chunk.decode("utf-8").replace("data: ", ""))
            content = decoded_chunk.get("content")
            tool = decoded_chunk.get("tool")
            arguments = decoded_chunk.get("arguments")
            tool_result = decoded_chunk.get("toolResult")
            # emotion = decoded_chunk.get("emotion")
            # action = decoded_chunk.get("action")

            if content:
                full_response += content
                placeholder.markdown(full_response)

            if tool:
                current_tool = tool
                current_tool_arguments = arguments

            if tool_result:
                with st.expander(f"🛠️ 工具调用: {current_tool}", expanded=False):
                    tool_md = f"```json\nArguments: {current_tool_arguments}\nToolResult: {tool_result}\n```\n"
                    st.markdown(tool_md)

                    # 将参考文档添加到历史消息中
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": tool_md,
                            "type": "tool",  # 添加类型标记
                            "tool": current_tool,
                        }
                    )

    return full_response


def display_chat_history():
    """
    显示聊天历史
    """
    for message in st.session_state.messages:
        # 根据消息类型使用不同的显示方式
        if message.get("type") == "reference":
            with st.chat_message("assistant"):
                with st.expander("📒 参考文档"):
                    st.markdown(message["content"])

        elif message.get("type") == "tool":
            with st.chat_message("assistant"):
                with st.expander(f"🛠️ 工具调用: {message.get('tool')}"):
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
        with st.expander("📒 参考文档"):
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
        with st.spinner("生成回答中", show_time=True):
            message_placeholder = st.empty()

            # 获取并处理响应
            response = get_stream_response(query)
            full_response = process_stream_response(response, message_placeholder)

            for i in range(len(st.session_state.messages) - 1, -1, -1):  # 从后向前遍历
                if st.session_state.messages[i].get("type") == "message":
                    st.session_state.messages[i]["content"] = full_response
                    break

            # 保存助手回复
            message_placeholder.markdown(full_response)
            for message in st.session_state.messages:
                if message.get("type") == "message":
                    message_placeholder.markdown(message["content"])

            # 获取引用文档
            documents = knowledge_controller.query_document(
                st.session_state.collection_select,
                query=query,
                precision_mode=st.session_state.precision_mode,
            )

            display_references(documents)


# TODO
def transcribe_audio(audio_bytes):
    """
    将音频转换为文本
    使用speech_recognition库处理音频并转为文本
    """
    return "暂不支持语音输入"


def main():
    """主函数"""

    # 添加自定义CSS使音频输入按钮固定在右下角
    # st.markdown(
    #     """
    # <style>
    # /* 语音输入按钮容器 */
    # .stAudioInput {
    #     position: fixed;
    #     bottom: 20%;
    # }
    # </style>
    # """,
    #     unsafe_allow_html=True,
    # )

    # 初始化页面
    chat_container = st.container()

    # init_welcome_page()
    initialize_page()
    render_sidebar()

    # 显示聊天界面
    with chat_container:
        display_chat_history()

    # 使用callback方式存储录音数据到session_state
    # audio_bytes = st.audio_input(
    #     "🎤",
    #     key="audio_recorder",
    #     label_visibility="hidden",
    # )

    # # 语音处理逻辑
    # if audio_bytes is not None:
    #     with st.spinner("正在识别语音..."):
    #         text = transcribe_audio(audio_bytes)
    #         if text:
    #             handle_user_input(text)

    # 正常使用chat_input
    if query := st.chat_input("你想说什么?", accept_file="multiple"):
        handle_user_input(query.get("text"))


main()
