"""
从EXCEL读取，每天更新的'福州南站综控室班计划作业记录表'
1. 根据车次获取开车时间，如果开车时间和现在<=5min，则提醒乘客可能来不及，需要到服务台进行改签，如果5-10min，则告诉乘客检票口，并告诉乘客离开车时间很近了，请尽快检票，如果10min+，则告诉乘客检票口
"""

import os
import re
from datetime import datetime
from typing import Annotated, Dict, Optional, Tuple

import pandas as pd
from haystack.tools import tool

from chat2rag.core.logger import get_logger

logger = get_logger(__name__)

# 全局缓存字典，存储文件路径 -> (修改时间, 结果) 的映射
_excel_cache: Dict[str, Tuple[float, Tuple[Optional[str], Optional[pd.DataFrame]]]] = {}


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
    # 移除空格并转为大写
    train_number = train_number.strip().upper()

    # 中文到英文的映射
    chinese_to_english = {
        "动": "D",
        "动车": "D",
        "高": "G",
        "高铁": "G",
        "城": "C",
        "和谐": "CRH",  # 和谐号动车组
        "复兴": "CR",  # 复兴号动车组
    }

    # 使用正则表达式匹配中文前缀
    for chinese, english in chinese_to_english.items():
        pattern = f"^{chinese}(\d+)$"
        match = re.match(pattern, train_number)
        if match:
            number = match.group(1)
            return f"{english}{number}"

    # 如果已经是标准格式或无法识别，直接返回
    return train_number


def find_today_sheet(excel_file):
    """
    从右到左遍历所有工作表，查找Q2单元格日期为今天的工作表
    支持基于文件修改时间的缓存机制

    Args:
        excel_file: Excel文件路径

    Returns:
        tuple: (工作表名称, DataFrame) 或 (None, None)
    """
    try:
        # 获取文件的修改时间
        file_mtime = os.path.getmtime(excel_file)

        # 检查缓存
        if excel_file in _excel_cache:
            cached_mtime, cached_result = _excel_cache[excel_file]
            if cached_mtime == file_mtime:
                logger.debug(f"使用缓存结果: {excel_file}")
                return cached_result

        # 文件已变更或首次访问，重新读取
        logger.debug(f"文件已变更或首次读取，重新解析: {excel_file}")

        # 读取Excel文件的所有工作表
        excel_data = pd.ExcelFile(excel_file)
        sheet_names = excel_data.sheet_names

        # 获取今天的日期
        today = datetime.now().date()

        # 从右到左遍历工作表
        for sheet_name in reversed(sheet_names):
            try:
                # 读取工作表，只读取前几行来获取R2单元格
                df_header = pd.read_excel(excel_file, sheet_name=sheet_name, header=None, nrows=5)

                # R2单元格对应第2行第17列（R列，索引从0开始所以是17）
                if len(df_header.columns) > 17 and len(df_header) > 1:
                    q2_value = df_header.iloc[1, 17]  # 第2行第17列

                    if pd.notna(q2_value):
                        # 尝试解析日期
                        try:
                            sheet_date = None

                            # 如果是数字（Excel日期序列号）
                            if isinstance(q2_value, (int, float)):
                                # Excel日期序列号转换为日期
                                # Excel的日期系统从1900年1月1日开始，但有闰年bug，所以用1899-12-30作为起点
                                sheet_date = pd.to_datetime(q2_value, origin="1899-12-30", unit="D").date()

                            # 如果是字符串，尝试解析
                            elif isinstance(q2_value, str):
                                # 可能的日期格式：2025年11月21日、2025-11-21等
                                date_str = (
                                    q2_value.replace("年", "-").replace("月", "-").replace("日", "").replace(" ", "")
                                )
                                sheet_date = datetime.strptime(date_str, "%Y-%m-%d").date()

                            # 如果是datetime对象
                            elif isinstance(q2_value, datetime):
                                sheet_date = q2_value.date()

                            # 其他情况尝试pandas转换
                            else:
                                sheet_date = pd.to_datetime(q2_value).date()

                            # 检查是否是今天
                            if sheet_date and sheet_date == today:
                                # 读取完整的数据表
                                df = pd.read_excel(excel_file, sheet_name=sheet_name, skiprows=3, header=None)
                                result = (sheet_name, df)

                                # 更新缓存
                                _excel_cache[excel_file] = (file_mtime, result)
                                return result

                        except (ValueError, TypeError, pd.errors.OutOfBoundsDatetime) as e:
                            # 日期解析失败，继续下一个工作表
                            logger.warning(f"解析工作表 {sheet_name} 的日期失败: {q2_value}, 错误: {e}")
                            continue

            except Exception as e:
                # 读取工作表失败，继续下一个
                logger.warning(f"读取工作表 {sheet_name} 失败: {e}")
                continue

        # 如果没找到今天的工作表，返回最后一个工作表（最新的）
        if sheet_names:
            last_sheet = sheet_names[-1]
            df = pd.read_excel(excel_file, sheet_name=last_sheet, skiprows=3, header=None)
            result = (last_sheet, df)

            # 更新缓存
            _excel_cache[excel_file] = (file_mtime, result)
            return result

        result = (None, None)
        # 更新缓存
        _excel_cache[excel_file] = (file_mtime, result)
        return result

    except Exception as e:
        logger.warning(f"查找今天工作表时发生错误：{str(e)}")
        return None, None


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
        # 标准化车次号
        normalized_train_number = normalize_train_number(train_number)

        # 读取Excel文件 - 需要根据实际文件路径调整
        excel_file = "uploads/ticket/福州南站综控室班计划作业记录表.xlsx"  # 根据实际文件路径调整

        if not os.path.exists(excel_file):
            return f"错误：找不到班计划作业记录表文件 {excel_file}"

        # 查找今天的工作表
        sheet_name, df = find_today_sheet(excel_file)

        # 手动设置列名，根据实际表格结构调整
        column_names = [
            "序号",
            "车次",
            "运行区段",
            "到达时刻",
            "开车时刻",
            "编组图定辆数",
            "编组实际辆数",
            "编组图定正反",
            "编组实际正反",
            "站台图定",
            "站台实际",
            "检票口",
            "进站客运作业完毕",
            "检票开检停检",
            "晚点时分到发",
            "上水开始结束",
            "上水车厢号",
            "吸污开始结束",
            "乘降完毕一趟一清",
            "备注",
        ]

        # 确保列数匹配，如果不匹配则使用实际列数
        if len(df.columns) != len(column_names):
            # 如果列数不匹配，使用通用列名
            df.columns = [f"col_{i}" for i in range(len(df.columns))]
            # 尝试根据位置推断关键列
            train_col = "col_1"  # 假设车次在第2列
            departure_col = "col_4"  # 假设开车时刻在第5列
            gate_col = "col_9"  # 假设检票口在第10列
        else:
            df.columns = column_names
            train_col = "车次"
            departure_col = "开车时刻"
            gate_col = "检票口"

        # 查找对应车次
        train_row = None
        potential_matches = []  # 存储可能的匹配车次

        for idx, row in df.iterrows():
            if pd.notna(row.get(train_col)):
                # 清理数据中的车次号（去除★◆等符号）
                db_train_number = str(row[train_col]).strip().replace("★", "").replace("◆", "").upper()
                db_train_only_number = db_train_number.replace("G", "").replace("C", "").replace("D", "")

                # 精确匹配完整车次号
                if db_train_number == normalized_train_number:
                    train_row = row
                    break

                # 如果输入的是纯数字，收集所有可能的匹配
                elif db_train_only_number == normalized_train_number:
                    potential_matches.append((db_train_number, row))

        # 如果没有精确匹配，处理数字匹配的情况
        if train_row is None and potential_matches:
            if len(potential_matches) == 1:
                # 只有一条匹配，直接使用
                train_row = potential_matches[0][1]
            else:
                # 多条匹配，询问用户选择
                train_options = [match[0] for match in potential_matches]
                return f"找到多个车次包含号码 {normalized_train_number}：{', '.join(train_options)}，请指定具体车次号"

        if train_row is None:
            return f"未找到车次 {normalized_train_number} 的信息，请确认车次号是否正确"

        # 获取开车时间和检票口
        departure_time_str = str(train_row.get(departure_col, "")).strip()
        train_number_formated = str(train_row.get(train_col, "")).strip().replace("★", "").replace("◆", "").upper()
        gate_info = str(train_row.get(gate_col, "")).strip()

        if not departure_time_str or departure_time_str == "nan":
            return f"车次 {normalized_train_number} 的开车时间信息不完整"

        # 解析开车时间
        try:
            # 假设时间格式为 HH:MM
            departure_hour, departure_minute, _ = map(int, departure_time_str.split(":"))

            # 获取当前时间
            now = datetime.now()

            # 构建今天的开车时间
            departure_today = now.replace(hour=departure_hour, minute=departure_minute, second=0, microsecond=0)

            # 计算时间差（分钟）
            time_diff = (departure_today - now).total_seconds() / 60

        except ValueError:
            return f"车次 {normalized_train_number} 的开车时间格式错误：{departure_time_str}"

        # 格式化检票口信息
        gate_text = f"检票口：{gate_info}" if gate_info and gate_info != "nan" else "检票口信息暂未更新"

        #

        # 根据时间差返回不同建议
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
        excel_file = "uploads/福州南站综控室班计划作业记录表.xlsx"

        if not os.path.exists(excel_file):
            return f"错误：找不到班计划作业记录表文件 {excel_file}"

        df = pd.read_excel(excel_file)

        current_time = datetime.now()
        current_hour = current_time.hour

        # 筛选当前时间前后2小时的列车
        relevant_trains = []

        for idx, row in df.iterrows():
            if pd.notna(row.get("车次")) and pd.notna(row.get("开车时刻")):
                try:
                    departure_time_str = str(row["开车时刻"]).strip()
                    departure_hour = int(departure_time_str.split(":")[0])

                    # 检查是否在当前时间前后2小时内
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


# if __name__ == "__main__":
#     print(get_train_info("D2431"))
