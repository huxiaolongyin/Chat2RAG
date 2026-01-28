import json
from typing import Generator

import requests
from config import CONFIG

from chat2rag.core.exceptions import ParseError
from chat2rag.core.logger import get_logger
from chat2rag.schemas.chat import ChatQueryParams, StreamChunkV1

logger = get_logger(__name__)
CHAT_V1_BASE_URL = f"{CONFIG.BASE_URL}/api/v1/chat/query-stream"


class ChatService:
    """聊天服务类，处理业务逻辑"""

    def __init__(self):
        self.session = requests.Session()

    def send_query(self, query_params: ChatQueryParams) -> requests.Response:
        """发送查询请求"""
        return requests.get(
            CHAT_V1_BASE_URL,
            params=query_params.model_dump(by_alias=True),
            stream=True,
            timeout=30,  # 超时
        )

    def process_stream_response(self, response: requests.Response) -> Generator[StreamChunkV1, None, None]:
        """处理流式响应，返回数据块生成器"""
        try:
            for chunk in response.iter_lines():
                if chunk:
                    try:
                        # 清理数据格式
                        chunk_str = chunk.decode("utf-8")
                        if chunk_str.startswith("data: "):
                            chunk_str = chunk_str[6:]  # 移除 "data: " 前缀

                        chunk_data = json.loads(chunk_str)
                        yield StreamChunkV1.model_validate(chunk_data, by_alias=True)

                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON: {str(e)}")
                        continue
                    except UnicodeDecodeError as e:
                        logger.warning(f"Failed to decode content: {str(e)}")
                        continue

        except Exception as e:
            raise ParseError(f"处理流式响应时发生错误: {str(e)}")

    def __del__(self):
        """清理资源"""
        if hasattr(self, "session"):
            self.session.close()


chat_service = ChatService()
