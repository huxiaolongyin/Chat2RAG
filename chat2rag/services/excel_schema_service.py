"""
Excel Schema 智能识别服务
- 上传时 LLM 识别前10行，生成 schema.json
- 后续读取时加载缓存的 schema
"""

import json
import re
from pathlib import Path
from typing import Optional

import pandas as pd

from chat2rag.core.logger import get_logger
from chat2rag.utils.llm_client import LLMClient

logger = get_logger(__name__)

SCHEMA_PROMPT = """分析这个Excel表格数据，识别其结构并提取指定字段的位置。

表格数据（前10行）：
{excel_data}

请识别以下字段在哪一列（返回列索引，从0开始）：
1. 车次 - 列车车次号
2. 开车时刻 - 列车出发时间
3. 检票口 - 检票口信息

同时识别：
1. 表头有多少行？（数据从第几行开始）

请返回JSON格式（不要包含```json标记）：
{{
  "header_rows": 3,
  "data_start_row": 4,
  "columns": {{
    "车次": {{"col_index": 1}},
    "开车时刻": {{"col_index": 4}},
    "检票口": {{"col_index": 9}}
  }}
}}

注意：
- 列索引从0开始
- 如果找不到某个字段，col_index设为-1"""


def _read_excel_preview(file_path: Path, nrows: int = 12) -> str:
    """读取Excel前N行，格式化为文本供LLM分析"""
    df = pd.read_excel(file_path, header=None, nrows=nrows)

    lines = []
    for idx, row in df.iterrows():
        cells = []
        for col_idx, val in enumerate(row):
            if pd.notna(val):
                cells.append(f"[{col_idx}]{val}")
        lines.append(f"Row{idx}: " + " | ".join(cells))

    return "\n".join(lines)


def _parse_schema_response(response: str) -> dict:
    """解析LLM返回的JSON"""
    response = response.strip()

    if "```" in response:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
        if match:
            response = match.group(1).strip()

    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse schema JSON: {e}")
        return _default_schema()


def _default_schema() -> dict:
    """默认schema（LLM识别失败时使用）"""
    return {
        "header_rows": 8,
        "data_start_row": 9,
        "columns": {
            "车次": {"col_index": 2},
            "开车时刻": {"col_index": 5},
            "检票口": {"col_index": 8},
        },
    }


async def recognize_and_save_schema(file_path: Path) -> dict:
    """
    LLM识别Excel前10行，保存schema.json

    Args:
        file_path: Excel文件路径

    Returns:
        schema字典
    """
    file_path = Path(file_path)
    schema_path = file_path.parent / "schema.json"

    excel_data = _read_excel_preview(file_path)
    prompt = SCHEMA_PROMPT.format(excel_data=excel_data)

    llm_client = LLMClient()
    response = await llm_client.acall_llm(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.0,
        extra_log="Excel Schema",
    )

    schema = _parse_schema_response(response)

    with open(schema_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, ensure_ascii=False, indent=2)
    logger.info(f"Schema saved to: {schema_path}")

    return schema


def load_schema(schema_path: Path) -> Optional[dict]:
    """
    加载缓存的schema.json

    Args:
        schema_path: schema.json路径

    Returns:
        schema字典，不存在返回None
    """
    schema_path = Path(schema_path)

    if not schema_path.exists():
        return None

    try:
        with open(schema_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load schema: {e}")
        return None


def read_excel_with_schema(file_path: Path) -> pd.DataFrame:
    """
    按schema读取Excel数据

    Args:
        file_path: Excel文件路径

    Returns:
        DataFrame，列名为：车次、开车时刻、检票口
    """
    file_path = Path(file_path)
    schema_path = file_path.parent / "schema.json"

    schema = load_schema(schema_path)
    if not schema:
        logger.warning(f"Schema not found: {schema_path}, using default")
        schema = _default_schema()

    columns = schema.get("columns", {})
    skip_rows = schema.get("data_start_row", 4) - 1

    df = pd.read_excel(file_path, header=None, skiprows=skip_rows)

    result_df = pd.DataFrame()
    for col_name in ["车次", "开车时刻", "检票口"]:
        col_idx = columns.get(col_name, {}).get("col_index", -1)
        if col_idx >= 0 and col_idx < len(df.columns):
            result_df[col_name] = df.iloc[:, col_idx]
        else:
            result_df[col_name] = None

    return result_df
