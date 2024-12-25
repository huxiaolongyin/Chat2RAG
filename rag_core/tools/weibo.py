import requests
import json


def get_weibo_info() -> str:
    """获取最新热度新闻"""
    url = "https://zj.v.api.aa1.cn/api/weibo-rs"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return json.dumps([item.get("title") for item in data.get("data")][:20])
    else:
        return "获取微博热搜失败"


weibo_info = {
    "type": "function",
    "function": {
        "name": "weibo_tool",
        "description": "当询问最新热度新闻时使用，用于获取最新的微博热搜新闻信息",
        "parameters": {},
    },
}
