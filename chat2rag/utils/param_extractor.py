import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExtractedParam:
    """提取的参数结果"""

    raw_value: str
    normalized_value: Optional[int | str] = None
    param_type: str = "none"


CHINESE_NUM_MAP = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "壹": 1,
    "二": 2,
    "贰": 2,
    "两": 2,
    "三": 3,
    "叁": 3,
    "四": 4,
    "肆": 4,
    "五": 5,
    "伍": 5,
    "六": 6,
    "陆": 6,
    "七": 7,
    "柒": 7,
    "八": 8,
    "捌": 8,
    "九": 9,
    "玖": 9,
    "十": 10,
    "拾": 10,
    "百": 100,
    "佰": 100,
    "千": 1000,
    "仟": 1000,
    "万": 10000,
    "萬": 10000,
}

ENGLISH_NUM_MAP = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
    "hundred": 100,
    "thousand": 1000,
}


def extract_arabic_number(text: str) -> Optional[int]:
    """提取阿拉伯数字"""
    match = re.search(r"\d+", text)
    if match:
        return int(match.group())
    return None


def chinese_to_number(chinese: str) -> Optional[int]:
    """将中文数字转换为阿拉伯数字"""
    chinese = chinese.strip()
    if not chinese:
        return None

    if chinese in CHINESE_NUM_MAP and CHINESE_NUM_MAP[chinese] < 10:
        return CHINESE_NUM_MAP[chinese]

    result = 0
    temp = 0

    for char in chinese:
        if char not in CHINESE_NUM_MAP:
            continue
        num = CHINESE_NUM_MAP[char]

        if num >= 10:
            if temp == 0:
                temp = 1
            result += temp * num
            temp = 0
        else:
            temp = num

    result += temp

    return result if result > 0 else None


def extract_chinese_number(text: str) -> Optional[int]:
    """从文本中提取中文数字"""
    chinese_num_pattern = (
        r"[零〇一二三四五六七八九十百千万两壹贰叁肆伍陆柒捌玖拾佰仟萬]+"
    )
    match = re.search(chinese_num_pattern, text)
    if match:
        return chinese_to_number(match.group())
    return None


def english_to_number(text: str) -> Optional[int]:
    """将英文数字转换为阿拉伯数字"""
    text = text.lower().strip()

    if text in ENGLISH_NUM_MAP:
        return ENGLISH_NUM_MAP[text]

    words = text.replace("-", " ").split()
    if not words:
        return None

    result = 0
    current = 0

    for word in words:
        if word not in ENGLISH_NUM_MAP:
            continue
        num = ENGLISH_NUM_MAP[word]

        if num == 100:
            if current == 0:
                current = 1
            current *= 100
        elif num == 1000:
            if current == 0:
                current = 1
            result += current * 1000
            current = 0
        else:
            current += num

    result += current

    return result if result > 0 else None


def extract_english_number(text: str) -> Optional[int]:
    """从文本中提取英文数字"""
    english_words = list(ENGLISH_NUM_MAP.keys())
    pattern = (
        r"\b(?:"
        + "|".join(english_words)
        + r")(?:\s+(?:"
        + "|".join(english_words)
        + r"))*\b"
    )
    match = re.search(pattern, text.lower())
    if match:
        return english_to_number(match.group())
    return None


def extract_number(text: str) -> Optional[int]:
    """
    从文本中提取数字（支持阿拉伯数字、中文数字、英文数字）

    优先级：阿拉伯数字 > 中文数字 > 英文数字

    Args:
        text: 输入文本，如 "音量调整到五十"、"volume to fifty"、"set to 100"

    Returns:
        提取到的数字，如 50, 50, 100；如果没有找到返回 None
    """
    if not text:
        return None

    result = extract_arabic_number(text)
    if result is not None:
        return result

    result = extract_chinese_number(text)
    if result is not None:
        return result

    result = extract_english_number(text)
    if result is not None:
        return result

    return None


def match_pattern(
    text: str, pattern: str, param_name: str = "num"
) -> Optional[ExtractedParam]:
    """
    使用模式匹配提取参数

    Args:
        text: 用户输入文本，如 "音量调整到五十"
        pattern: 匹配模式，如 "音量调整到{num}" 或 "音量调整到{num}|把音量调到{num}"
        param_name: 参数名称，默认为 "num"

    Returns:
        ExtractedParam 对象，包含原始值和转换后的值
    """
    if not text or not pattern:
        return None

    patterns = [p.strip() for p in pattern.split("|") if p.strip()]
    placeholder = f"{{{param_name}}}"

    for p in patterns:
        if placeholder not in p:
            continue

        regex_pattern = re.escape(p).replace(re.escape(placeholder), r"(.+)")
        match = re.search(regex_pattern, text)
        if match:
            raw_value = match.group(1).strip()
            number = extract_number(raw_value)

            return ExtractedParam(
                raw_value=raw_value, normalized_value=number, param_type="number"
            )

    return None


def extract_param_from_text(
    text: str, param_type: str = "number"
) -> Optional[ExtractedParam]:
    """
    从文本中直接提取参数（不依赖模式）

    Args:
        text: 用户输入文本
        param_type: 参数类型

    Returns:
        ExtractedParam 对象
    """
    if not text:
        return None

    if param_type == "number":
        number = extract_number(text)
        if number is not None:
            return ExtractedParam(
                raw_value=str(number), normalized_value=number, param_type="number"
            )

    return None
