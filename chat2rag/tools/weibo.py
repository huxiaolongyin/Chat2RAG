import json

import requests
from haystack.tools import tool


@tool
def get_weibo_info() -> str:
    "用于获取最新的微博热搜新闻信息，当询问最新热度新闻时使用"
    url = "http://zj.v.api.aa1.cn/api/weibo-rs/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return json.dumps([item.get("title") for item in data.get("data")][:20])
    else:
        return "获取微博热搜失败"
