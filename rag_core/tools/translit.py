from rag_core.config import CONFIG
import requests

key = CONFIG.GAODE_API_KEY


def format_route_to_text(route_result: dict) -> str:
    """将高德路径规划的公交API返回结果转换为自然语言描述

    Args:
        route_result: 高德API返回的路径规划结果
    Returns:
        str: 自然语言描述
    """
    if not route_result or "route" not in route_result:
        return "未能获取到路线信息"
    route = route_result["route"]
    transits = route["transits"][0]  # 取第一条推荐路线
    segments = transits["segments"]

    # 提取基本信息
    total_duration = int(transits["duration"]) // 60  # 转换为分钟
    total_distance = int(transits["distance"]) // 1000  # 转换为公里

    # 构建路线描述
    route_desc = []
    route_desc.append(f"全程约{total_distance}公里，预计耗时{total_duration}分钟。")

    for idx, segment in enumerate(segments, 1):
        if segment.get("walking"):
            walking = segment["walking"]
            distance = int(walking.get("distance", "0"))
            duration = int(walking.get("duration", "0")) // 60
            steps = walking.get("steps", [])
            arrive = steps[-1]["assistant_action"]

            route_desc.append(
                f"第{idx}步: 步行{distance}米, 共计{duration}分钟, {arrive}"
            )

        if segment.get("bus"):
            bus = segment["bus"]
            buslines = bus.get("buslines", [])
            for line in buslines:
                departure = line["departure_stop"]["name"]
                arrival = line["arrival_stop"]["name"]
                bus_name = line["name"].split("(")[0]

                route_desc.append(
                    f"第{idx}步: 从{departure}站乘坐{bus_name}到{arrival}站。"
                )
    route_desc.append("到达目的地")
    return "\n".join(route_desc)


def get_gps_coordinates(address: str, city: str) -> str:
    """
        给定地址信息, 通过高德服务, 返回 GPS 坐标
    Args:
        address: 地址名称
        city: 城市名称
    Returns:
        str: 高德地图地址信息
    """
    url = "https://restapi.amap.com/v3/geocode/geo"
    response = requests.get(
        url=url,
        params={"key": key, "address": address, "city": city},
    )
    # todo: 多个地址的选择
    return response.json()["geocodes"][0]["location"]


def get_city_name_from_gps(gps: str) -> str:
    """
        输入GPS信息, 通过高德服务, 返回城市名称
    Args:
        gps: 地址 gps 坐标
    Returns:
        str: 城市信息
    """
    url = "https://restapi.amap.com/v3/geocode/regeo"
    response = requests.get(
        url=url,
        params={"key": key, "location": gps},
    )
    return response.json()["regeocode"]["addressComponent"]["city"]


def get_gaode_route(
    origin: str,
    destination: str,
    city: str,
) -> dict:
    """获取高德地图路径规划结果
    Args:
        origin: 起点 gps 坐标
        destination: 终点 gps 坐标
        city: 城市名称
    Returns:
        dict: 高德地图路径规划结果
    """
    url = "https://restapi.amap.com/v3/direction/transit/integrated"
    response = requests.get(
        url=url,
        params={"key": key, "origin": origin, "destination": destination, "city": city},
    )
    return response.json()


def get_translit_info(
    origin: str = None,
    destination: str = None,
):
    """
        获取高德地图路径规划结果
    Args:
        origin: 起点 gps 坐标
        destination: 终点名称
    Returns:
        str: 高德地图路径规划结果
    """
    if origin is None:
        origin = "119.235434,26.062731"
    # 根据起点坐标获取起点的城市
    origin_city = get_city_name_from_gps(origin)

    # 获取目的地的经纬度
    destination = get_gps_coordinates(destination, origin_city)

    # 获取路径规划结果
    route_json = get_gaode_route(origin, destination, origin_city)

    # 解析成自然语言描述
    return format_route_to_text(route_json)


translit_info = {
    "type": "function",
    "function": {
        "name": "translit_tool",
        "description": "仅在询问路线规划时使用, 用于获取高德地图路径规划结果",
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "str",
                    "description": "终点名称, 请给出明确名称; 如: 厦门大学",
                },
            },
            "required": ["destination"],
        },
    },
}
