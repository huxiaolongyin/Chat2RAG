import json
import requests
from fuzzywuzzy import process
from rag_core.config import CONFIG


def get_weather_info(city_name: str = None) -> str:
    """获取城市当前的天气信息"""
    key = CONFIG.GAODE_API_KEY
    if not city_name:
        ip_get_url = f"https://restapi.amap.com/v3/ip?key={key}"
        response = requests.get(ip_get_url)
        if response.status_code == 200:
            city_code = response.json()["adcode"]
        else:
            return "获取位置信息失败"
    else:
        city_code = find_city_code(city_name)

    url = f"https://restapi.amap.com/v3/weather/weatherInfo?key={key}&city={city_code}"

    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        weather_info = data["lives"][0]
        return json.dumps(weather_info, ensure_ascii=False)
    else:
        return "获取天气信息失败"


def find_city_code(city_name):
    """根据城市名称找到城市代码"""
    with open(str(CONFIG.DATA_DIR) + "/city_code.json", "r", encoding="utf-8") as f:
        # 直接加载JSON数组
        city_list = json.load(f)

        # 创建城市名称到代码的映射字典
        city_dict = {item["province"]: item["city_code"] for item in city_list}

        # 使用fuzzywuzzy进行模糊匹配
        best_match = process.extractOne(city_name, city_dict.keys())

        if best_match[1] >= 80:  # 匹配度阈值80%
            return city_dict[best_match[0]]

        return None


# 仅在用户明确询问天气、温度、降水、气温等气象信息时使用，获取指定城市的当前天气情况，如果用户没有指定城市，则返回空值以获取当地天气情况。
weather_info = {
    "type": "function",
    "function": {
        "name": "weather_tool",
        "description": "询问天气、温度、降水、气温等气象信息时使用，默认为空值，获取当地天气情况。",
        "parameters": {
            "type": "object",
            "properties": {
                "city_name": {
                    "type": "string",
                    "description": "中国城市的名称，如果不指定则会返回空值",
                }
            },
        },
    },
}
