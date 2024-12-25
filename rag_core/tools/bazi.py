from datetime import datetime
from lunar_python import Lunar, Solar


def get_constellation(month, day):
    """
    根据月份和日期判断星座
    """
    dates = (
        (1, 20),
        (2, 19),
        (3, 21),
        (4, 20),
        (5, 21),
        (6, 22),
        (7, 23),
        (8, 23),
        (9, 23),
        (10, 24),
        (11, 23),
        (12, 22),
    )
    constellations = (
        "水瓶座",
        "双鱼座",
        "白羊座",
        "金牛座",
        "双子座",
        "巨蟹座",
        "狮子座",
        "处女座",
        "天秤座",
        "天蝎座",
        "射手座",
        "摩羯座",
    )

    if day < dates[month - 1][1]:
        return constellations[month - 1]
    else:
        return constellations[month % 12]


def get_bazi_info(date_str, hour):
    """
    计算生辰八字和五行属性
    参数:
        date_str: 阳历日期字符串，格式为 'YYYY-MM-DD'
        hour: 小时 (0-23)
    返回:
        包含八字和五行信息的字典
    """
    # 解析日期
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")

    year = date_obj.year
    month = date_obj.month
    day = date_obj.day

    # 创建阳历对象
    solar = Solar.fromYmdHms(year, month, day, hour, 0, 0)
    # 转换为农历对象
    lunar = Lunar.fromSolar(solar)

    # 获取八字信息
    bazi_info = {
        "年柱": lunar.getYearInGanZhi(),
        "月柱": lunar.getMonthInGanZhi(),
        "日柱": lunar.getDayInGanZhi(),
        "时柱": lunar.getTimeInGanZhi(),
        "年柱五行": lunar.getYearNaYin(),
        "月柱五行": lunar.getMonthNaYin(),
        "日柱五行": lunar.getDayNaYin(),
        "时柱五行": lunar.getTimeNaYin(),
        "生肖": lunar.getYearShengXiao(),
        "农历日期": f"{lunar.getYearInChinese()}年{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}",
        "星座": get_constellation(month, day),
    }

    return bazi_info


bazi_info = {
    "type": "function",
    "function": {
        "name": "bazi_tool",
        "description": "通过阳历日期和小时计算生辰八字和五行属性， 需要用户明确提供阳历日期和小时",
        "parameters": {
            "type": "object",
            "properties": {
                "date_str": {
                    "type": "string",
                    "description": "阳历日期，格式为 'YYYY-MM-DD'",
                },
                "hour": {
                    "type": "integer",
                    "description": "小时 (0-23)",
                },
            },
            "required": ["date", "hour"],
        },
    },
}
