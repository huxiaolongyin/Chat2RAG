from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.dataclasses import ChatMessage
from haystack.utils import Secret

from chat2rag.config import CONFIG

# 模块级别的单例客户端
_chat_client = None


def get_chat_client():
    """获取或创建OpenAI客户端单例"""
    global _chat_client
    if _chat_client is None:
        _chat_client = OpenAIChatGenerator(
            model="Qwen/Qwen2.5-14B-Instruct",
            api_key=Secret.from_env_var("OPENAI_API_KEY"),
            api_base_url=CONFIG.OPENAI_BASE_URL,
        )
    return _chat_client


async def ai_create_shortname(description):
    """
    使用AI生成工具的简称
    """
    client = get_chat_client()
    messages = [
        ChatMessage.from_user(
            f"请根据以下描述直接生成一个7字以内的简短的工具名称，名称应该简洁明了，易于理解。不必回复其他任何内容，直接返回名称即可。工具描述内容：{description}",
        )
    ]
    result = await client.run_async(messages)
    return result.get("replies")[0].text


if __name__ == "__main__":
    print(
        ai_create_shortname(
            "骑行路径规划用于规划骑行通勤方案，规划时会考虑天桥、单行线、封路等情况。最大支持 500km 的骑行路线规划"
        )
    )
