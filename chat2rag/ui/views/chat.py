import requests
import streamlit as st
from components.message_renderer import message_renderer
from config import CONFIG
from enums import MessageType
from haystack.dataclasses import ChatRole
from service.chat import chat_service
from service.knowledge import knowledge_service
from service.message import message_service
from utils.sidebar import render_sidebar

from chat2rag.exceptions import ChatServiceError, NetworkError, ParseError
from chat2rag.logger import get_logger
from chat2rag.schemas.chat import ChatQueryParams

logger = get_logger("chat2rag.ui")


class ChatUI:
    """聊天界面类"""

    def initialize_session(self):
        """初始化会话状态"""
        message_service.initialize_messages()

        # 初始化其他会话状态
        if "message_id" not in st.session_state:
            st.session_state["message_id"] = "default_chat"

    def _create_chat_params(self, query: str) -> ChatQueryParams:
        """创建聊天请求对象"""
        return ChatQueryParams(
            collection_name=st.session_state["collection_select"],
            query=query,
            top_k=st.session_state["topK"],
            score_threshold=st.session_state["threshold"],
            precision_mode=1 if st.session_state["precision_mode"] else 0,
            chat_id=str(st.session_state["message_id"]),
            prompt_name=st.session_state["prompt_select"],
            chat_rounds=CONFIG.DEFAULT_CHAT_ROUNDS,
            generator_model=st.session_state["model_select"],
        )

    def handle_user_input(self, query: str):
        """处理用户输入"""
        try:
            # 添加用户消息
            message_service.add_message(role=ChatRole.USER, content=query)

            # 显示用户消息
            with st.chat_message("user"):
                st.write(query)

            # 处理助手响应
            self._handle_assistant_response(query)

        except Exception as e:
            logger.error(f"处理用户输入时发生错误: {e}")
            st.error(f"处理消息时发生错误: {str(e)}")

    def _handle_assistant_response(self, query: str):
        """处理助手响应"""
        with st.chat_message("assistant"):
            with st.spinner(CONFIG.SPINNER_TEXT):
                message_placeholder = st.empty()

                try:
                    # 创建请求并发送
                    chat_params = self._create_chat_params(query)
                    response = chat_service.send_query(chat_params)

                    # 添加空的助手消息占位符
                    message_service.add_message(role=ChatRole.ASSISTANT, content="")

                    # 处理流式响应
                    full_response = self._process_stream_response(response, message_placeholder)

                    # 更新最终消息内容
                    message_service.update_last_message(content=full_response)

                    # 获取并显示参考文档
                    self._handle_references(query)

                except NetworkError as e:
                    st.error(f"网络错误: {str(e)}")
                except ParseError as e:
                    st.error(f"数据解析错误: {str(e)}")
                except ChatServiceError as e:
                    st.error(f"服务错误: {str(e)}")
                except Exception as e:
                    logger.error(f"处理助手响应时发生未知错误: {e}")
                    st.error("处理响应时发生未知错误，请稍后重试")

    def _process_stream_response(self, response: requests.Response, placeholder) -> str:
        """处理流式响应"""
        full_response = ""

        try:
            for chunk in chat_service.process_stream_response(response):
                if chunk.content:
                    full_response += chunk.content
                    placeholder.markdown(full_response)

        except Exception as e:
            logger.error(f"处理流式响应时发生错误: {e}")
            st.error("处理响应流时发生错误")

        return full_response

    def _display_tool_result(self, tool: str, arguments: str, result: str):
        """显示工具调用结果"""
        with st.expander(f"🛠️ 工具调用: {tool}", expanded=False):
            tool_md = f"```json\nArguments: {arguments}\nToolResult: {result}\n```\n"
            st.markdown(tool_md)

            # 添加工具消息到历史
            message_service.add_message(
                role=ChatRole.ASSISTANT, content=tool_md, message_type=MessageType.TOOL, tool=tool
            )

    def _handle_references(self, query: str):
        """处理参考文档"""
        try:
            documents = knowledge_service.query_document(query=query)
            if documents:
                references_md = message_renderer.render_references(documents)

                # 添加参考文档到消息历史
                message_service.add_message(
                    role=ChatRole.SYSTEM, content=references_md, message_type=MessageType.REFERENCE
                )

        except Exception as e:
            logger.error(f"获取参考文档时发生错误: {e}")
            st.warning("获取参考文档时发生错误")

    def render(self):
        """渲染整个聊天界面"""
        # 初始化
        self.initialize_session()

        # 渲染侧边栏
        render_sidebar(clear_message=True)

        # 创建聊天容器
        chat_container = st.container()

        with chat_container:
            # 显示聊天历史
            messages = message_service.get_messages()
            message_renderer.render_messages(messages)

        # 处理用户输入
        if query := st.chat_input("你想说什么?", accept_file="multiple"):
            self.handle_user_input(query.text)


def main():
    """主函数"""
    chat_ui = ChatUI()
    chat_ui.render()


if __name__ == "__main__":
    main()

# def process_stream_response(response: requests.Response, placeholder):
#     """
#     处理流式响应
#     """
#     full_response = ""
#     current_tool = None
#     current_tool_arguments = None

#     # 添加聊天占位
#     st.session_state["messages"].append(
#         {
#             "role": "assistant",
#             "content": "",
#             "type": "message",  # 添加类型标记
#         }
#     )
#     for chunk in response.iter_lines():
#         if chunk:
#             decoded_chunk = json.loads(chunk.decode("utf-8").replace("data: ", ""))
#             content = decoded_chunk.get("content")
#             tool = decoded_chunk.get("tool")
#             arguments = decoded_chunk.get("arguments")
#             tool_result = decoded_chunk.get("toolResult")

#             if content:
#                 full_response += content
#                 placeholder.markdown(full_response)

#             if tool:
#                 current_tool = tool
#                 current_tool_arguments = arguments

#             if tool_result:
#                 with st.expander(f"🛠️ 工具调用: {current_tool}", expanded=False):
#                     tool_md = f"```json\nArguments: {current_tool_arguments}\nToolResult: {tool_result}\n```\n"
#                     st.markdown(tool_md)

#                     # 将参考文档添加到历史消息中
#                     st.session_state["messages"].append(
#                         {
#                             "role": "assistant",
#                             "content": tool_md,
#                             "type": "tool",  # 添加类型标记
#                             "tool": current_tool,
#                         }
#                     )

#     return full_response


# def display_chat_history():
#     """
#     显示聊天历史
#     """
#     for message in st.session_state["messages"]:
#         # 根据消息类型使用不同的显示方式
#         if message.get("type") == "reference":
#             with st.chat_message("assistant"):
#                 with st.expander("📒 参考文档"):
#                     st.markdown(message["content"])

#         elif message.get("type") == "tool":
#             with st.chat_message("assistant"):
#                 with st.expander(f"🛠️ 工具调用: {message.get('tool')}"):
#                     st.markdown(message["content"])
#         else:
#             with st.chat_message(message["role"]):
#                 st.markdown(message["content"])


# def display_references(documents: list):
#     """
#     在streamlit 显示文档引用
#     """
#     if documents:
#         # 构建参考文档的markdown格式
#         references_md = ""
#         for doc in documents:
#             references_md += f"文档（相关度: {doc['score']*100:.2f}%）：{doc['content']}\n\n"
#         # 显示当前参考文档
#         with st.expander("📒 参考文档"):
#             st.write(references_md)

#         # 将参考文档添加到历史消息中
#         st.session_state["messages"].append(
#             {
#                 "role": "system",
#                 "content": references_md,
#                 "type": "reference",  # 添加类型标记
#             }
#         )


# def handle_user_input(query: str):
#     """处理用户输入"""
#     # 添加用户消息
#     st.session_state["messages"].append({"role": "user", "content": query})
#     with st.chat_message("user"):
#         st.write(query)

#     # 处理助手响应
#     with st.chat_message("assistant"):
#         with st.spinner("生成回答中", show_time=True):
#             message_placeholder = st.empty()

#             query_params = ChatQueryParams(
#                 collection_name=st.session_state["collection_select"],
#                 query=query,
#                 top_k=st.session_state["topK"],
#                 score_threshold=st.session_state["threshold"],
#                 precision_mode=1 if st.session_state["precision_mode"] else 0,
#                 chat_id=str(st.session_state["message_id"]),
#                 prompt_name=st.session_state["prompt_select"],
#                 chat_rounds=CONFIG.DEFAULT_CHAT_ROUNDS,
#                 generator_model=st.session_state["model_select"],
#             )
#             response = chat_service.send_query(query_params)
#             full_response = process_stream_response(response, message_placeholder)

#             for i in range(len(st.session_state["messages"]) - 1, -1, -1):  # 从后向前遍历
#                 if st.session_state["messages"][i].get("type") == "message":
#                     st.session_state["messages"][i]["content"] = full_response
#                     break

#             # 保存助手回复
#             message_placeholder.markdown(full_response)
#             for message in st.session_state["messages"]:
#                 if message.get("type") == "message":
#                     message_placeholder.markdown(message["content"])

#             # 获取引用文档
#             documents = knowledge_controller.query_document(query=query)

#             display_references(documents)


# def main():
#     """主函数"""

#     # 初始化页面
#     chat_container = st.container()

#     # init_welcome_page()
#     # initialize_page()
#     render_sidebar(clear_message=True)

#     # 显示聊天界面
#     with chat_container:
#         display_chat_history()

#     # 正常使用chat_input
#     if query := st.chat_input("你想说什么?", accept_file="multiple"):
#         handle_user_input(query.get("text"))


# main()
