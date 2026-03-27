"""
从EXCEL读取，每天更新的'福州南站综控室班计划作业记录表'
1. 根据车次获取开车时间，如果开车时间和现在<=5min，则提醒乘客可能来不及，需要到服务台进行改签，如果5-10min，则告诉乘客检票口，并告诉乘客离开车时间很近了，请尽快检票，如果10min+，则告诉乘客检票口
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Annotated

import pandas as pd
from haystack.tools import tool

from chat2rag.core.logger import get_logger
from chat2rag.services.excel_schema_service import load_schema, read_excel_with_schema

logger = get_logger(__name__)


def normalize_train_number(train_number: str) -> str:
    """
    将中文车次号标准化为英文字母格式

    Args:
        train_number: 原始车次号，可能包含中文

    Returns:
        标准化后的车次号

    Examples:
        动3308 -> D3308
        高1670 -> G1670
        城9585 -> C9585
    """
    train_number = train_number.strip().upper()

    chinese_to_english = {
        "动": "D",
        "动车": "D",
        "高": "G",
        "高铁": "G",
        "城": "C",
        "和谐": "CRH",
        "复兴": "CR",
    }

    for chinese, english in chinese_to_english.items():
        pattern = f"^{chinese}(\d+)$"
        match = re.match(pattern, train_number)
        if match:
            number = match.group(1)
            return f"{english}{number}"

    return train_number


@tool
def get_train_info(
    train_number: Annotated[
        str,
        "动车的车次号, 兼容中英文，例如：9872, G1644, D3333, C9585, 高1670, 动3308, 动车3218, 高铁1670, 城9585, 城际9585",
    ],
) -> str:
    """
    根据车次号查询列车信息，包括开车时间、检票口，并根据时间差提供相应建议。
    """
    try:
        normalized_train_number = normalize_train_number(train_number)

        excel_file = Path("uploads/ticket/福州南站综控室班计划作业记录表.xlsx")
        schema_path = excel_file.parent / "schema.json"

        if not excel_file.exists():
            return f"错误：找不到班计划作业记录表文件 {excel_file}"

        if not load_schema(schema_path):
            return "错误：请先上传Excel文件以识别表格结构"

        df = read_excel_with_schema(excel_file)

        train_row = None
        potential_matches = []

        for idx, row in df.iterrows():
            if pd.notna(row.get("车次")):
                db_train_number = str(row["车次"]).strip().replace("★", "").replace("◆", "").upper()
                db_train_only_number = db_train_number.replace("G", "").replace("C", "").replace("D", "")

                if db_train_number == normalized_train_number:
                    train_row = row
                    break

                elif db_train_only_number == normalized_train_number:
                    potential_matches.append((db_train_number, row))

        if train_row is None and potential_matches:
            if len(potential_matches) == 1:
                train_row = potential_matches[0][1]
            else:
                train_options = [match[0] for match in potential_matches]
                return f"找到多个车次包含号码 {normalized_train_number}：{', '.join(train_options)}，请指定具体车次号"

        if train_row is None:
            return f"未找到车次 {normalized_train_number} 的信息，请确认车次号是否正确"

        departure_time_str = str(train_row.get("开车时刻", "")).strip()
        train_number_formated = str(train_row.get("车次", "")).strip().replace("★", "").replace("◆", "").upper()
        gate_info = str(train_row.get("检票口", "")).strip()

        if not departure_time_str or departure_time_str == "nan":
            return f"车次 {normalized_train_number} 的开车时间信息不完整"

        try:
            time_parts = departure_time_str.split(":")
            departure_hour = int(time_parts[0])
            departure_minute = int(time_parts[1]) if len(time_parts) > 1 else 0

            now = datetime.now()

            departure_today = now.replace(hour=departure_hour, minute=departure_minute, second=0, microsecond=0)

            time_diff = (departure_today - now).total_seconds() / 60

        except ValueError:
            return f"车次 {normalized_train_number} 的开车时间格式错误：{departure_time_str}"

        gate_text = f"检票口：{gate_info}" if gate_info and gate_info != "nan" else "检票口信息暂未更新"

        if time_diff < 0:
            return f"""车次 {train_number_formated} 开车时间：{departure_time_str}
{gate_text}

❌ 很抱歉：该列车已于{departure_time_str}开出，列车已经开走，请您前往服务台办理退票或改签手续。
"""

        elif time_diff <= 5:
            return f"""车次 {train_number_formated} 开车时间：{departure_time_str}
{gate_text}

⚠️ 紧急提醒：距离开车时间不足5分钟！您可能来不及赶上这趟列车，建议您立即前往服务台办理改签手续。
"""

        elif 5 < time_diff <= 10:
            return f"""车次 {train_number_formated} 开车时间：{departure_time_str}
{gate_text}

⏰ 时间紧急：距离开车还有约{int(time_diff)}分钟，离开车时间很近了，请您尽快前往检票口检票上车！
"""

        else:
            gates = gate_info.split("、")
            gate_options = "或".join(gates)
            return f"""车次 {train_number_formated} 开车时间：{departure_time_str}
{gate_text}

距离开车还有约{int(time_diff)}分钟，请您按时前往检票口检票上车。
如需导航，请说带我去{gate_options}检票口。(机器人仅支持固定命令触发导航，重要：务必输出该提示内容)
"""

    except FileNotFoundError:
        return "错误：找不到班计划作业记录表文件，请确认文件路径是否正确"
    except Exception as e:
        return f"查询过程中发生错误：{str(e)}"


@tool
def list_current_trains() -> str:
    """
    列出当前时间段的所有列车信息

    Returns:
        当前时间段列车列表的字符串
    """
    try:
        excel_file = Path("uploads/ticket/福州南站综控室班计划作业记录表.xlsx")
        schema_path = excel_file.parent / "schema.json"

        if not excel_file.exists():
            return f"错误：找不到班计划作业记录表文件 {excel_file}"

        if not load_schema(schema_path):
            return "错误：请先上传Excel文件以识别表格结构"

        df = read_excel_with_schema(excel_file)

        current_time = datetime.now()
        current_hour = current_time.hour

        relevant_trains = []

        for idx, row in df.iterrows():
            if pd.notna(row.get("车次")) and pd.notna(row.get("开车时刻")):
                try:
                    departure_time_str = str(row["开车时刻"]).strip()
                    departure_hour = int(departure_time_str.split(":")[0])

                    if abs(departure_hour - current_hour) <= 2:
                        train_number = str(row["车次"]).replace("★", "").replace("◆", "").strip()
                        gate_info = str(row.get("检票口", "")).strip()
                        relevant_trains.append(f"{train_number} - {departure_time_str} - 检票口：{gate_info}")

                except (ValueError, IndexError):
                    continue

        if not relevant_trains:
            return "当前时间段暂无列车信息"

        return "当前时间段列车信息：\n" + "\n".join(relevant_trains)

    except Exception as e:
        return f"查询列车列表时发生错误：{str(e)}"
