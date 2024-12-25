from datetime import datetime
from zhdate import ZhDate


def get_today_info():
    # Get current date
    today = datetime.now()

    # Basic date info
    weekday_map = {
        0: "星期一",
        1: "星期二",
        2: "星期三",
        3: "星期四",
        4: "星期五",
        5: "星期六",
        6: "星期日",
    }

    # Get lunar date
    lunar_date = ZhDate.from_datetime(today)

    # Get zodiac sign
    zodiac_signs = {
        (1, 20): "水瓶座",
        (2, 19): "双鱼座",
        (3, 21): "白羊座",
        (4, 20): "金牛座",
        (5, 21): "双子座",
        (6, 22): "巨蟹座",
        (7, 23): "狮子座",
        (8, 23): "处女座",
        (9, 23): "天秤座",
        (10, 24): "天蝎座",
        (11, 23): "射手座",
        (12, 22): "摩羯座",
    }

    month, day = today.month, today.day
    zodiac = None
    for (m, d), sign in zodiac_signs.items():
        if (month, day) <= (m, d):
            zodiac = sign
            break
    if not zodiac:
        zodiac = "摩羯座"

    result = {
        "公历日期": today.strftime("%Y年%m月%d日"),
        "星期": weekday_map[today.weekday()],
        "农历日期": f"{lunar_date.chinese()}",
        "星座": zodiac,
        "时间": today.strftime("%H:%M:%S"),
    }

    return result


today_info = {
    "type": "function",
    "function": {
        "name": "today_tool",
        "description": "询问今天日期、星期几、农历日期、农历星期几、节日、星座、黄历等时使用",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
}
