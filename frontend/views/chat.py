import json
import os
import random

import requests
import streamlit as st

# from pyinstrument import Profiler
# profiler = Profiler()
# profiler.start()

chat_container = st.container()

BACKEND_HOST = os.environ.get("BACKEND_HOST", "host.docker.internal")
BACKEND_PORT = os.environ.get("BACKEND_PORT", "8000")

# 如果 "messages" 不存在于会话状态中，则初始化它，用于加载历史消息
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "你好，有什么可以帮你的吗？"}
    ]
    st.session_state.message_id = random.randint(100000, 9000000)

with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

query = st.chat_input("你想说什么?")

if query:
    # 插入消息到会话状态中
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.write(query)
    with st.chat_message("assistant"):
        with st.spinner("生成回答中"):
            # 创建一个空的占位符用于更新内容
            message_placeholder = st.empty()
            full_response = ""

            response = requests.get(
                f"http://{BACKEND_HOST}:{BACKEND_PORT}/api/v1/chat/query-stream",
                params={
                    "query": query,
                    "batchOrStream": "stream",
                    "chatId": st.session_state.message_id,
                    "chatRounds": 5,
                    "toolList": ["all"],
                },
                stream=True,
            )

            for chunk in response.iter_lines():
                if chunk:
                    decoded_chunk = json.loads(
                        chunk.decode("utf-8").replace("data: ", "")
                    )
                    if decoded_chunk.get("content"):
                        full_response += decoded_chunk["content"]
                        # 实时更新显示的内容
                        message_placeholder.markdown(full_response)

            # 完成后显示最终内容
            message_placeholder.markdown(full_response)
            st.session_state.messages.append(
                {"role": "assistant", "content": full_response}
            )
            # profiler.stop()
            # print(profiler.output_text(unicode=True, color=True))
