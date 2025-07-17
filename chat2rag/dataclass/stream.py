from dataclasses import dataclass
from typing import List


@dataclass
class StreamConfig:
    """流式配置"""

    # 中文标点
    CN_SYMBOLS = ["，", "；", "。", "：", "？", "！", "\n"]
    # 英文标点
    EN_SYMBOLS = [",", ";", "?", "!"]

    # 批量大小
    batch_size: int = 50
    # 分隔符号
    split_symbols: List[str] = None

    def __post_init__(self):
        if self.split_symbols is None:
            self.split_symbols = self.CN_SYMBOLS + self.EN_SYMBOLS
