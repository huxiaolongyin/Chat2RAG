from .weather import *
from .weibo import *
from .translit import *
from .today import *
from .bazi import *
from .tool_manage import ToolManager

tool_manager = ToolManager()
tools_info = tool_manager.get_model_functions()
tools_name = tool_manager.get_tools_name()

tools = [weather_info, weibo_info, translit_info, today_info, bazi_info, *tools_info]
functions = {
    "weather_tool": get_weather_info,
    "weibo_tool": get_weibo_info,
    "translit_tool": get_translit_info,
    "today_tool": get_today_info,
    "bazi_tool": get_bazi_info,
}
