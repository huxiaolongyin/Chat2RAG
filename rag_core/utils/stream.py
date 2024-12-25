import datetime
import json
from queue import Queue
from dataclasses import dataclass
from typing import List, Optional


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


class StreamHandler:
    def __init__(self, config: Optional[StreamConfig] = None):
        self.queue = Queue()
        self.config = config or StreamConfig()

    def callback(self, chunk: str):
        self.queue.put(chunk)

    def _create_message(self, content: str, meta: dict) -> dict:
        """创建消息格式"""
        return {
            "object": "message",
            "content": content,
            "model": meta["model"],
            "isFinish": meta["finish_reason"] == "stop",
            "createTime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def _should_flush_batch(self, chunk: str, batch_content: str) -> bool:
        """判断是否需要输出当前批次"""
        return (
            chunk.content in self.config.split_symbols
            or chunk.content.rstrip() in self.config.split_symbols
            or len(batch_content) >= self.config.batch_size
        )

    def get_stream(self, is_batch: bool = False):
        if not is_batch:
            # 流式处理模式
            while True:
                chunk = self.queue.get()
                if chunk == "[END]":
                    break

                data = self._create_message(chunk.content, chunk.meta)
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
        else:
            # 批量处理模式
            current_batch = []
            while True:
                chunk = self.queue.get()
                if chunk == "[END]":
                    # 处理最后一批数据
                    if current_batch:
                        combined_content = "".join([c.content for c in current_batch])
                        data = self._create_message(
                            combined_content, current_batch[-1].meta
                        )
                        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                    break

                current_batch.append(chunk)

                batch_content = "".join([c.content for c in current_batch])
                if self._should_flush_batch(chunk, batch_content):
                    data = self._create_message(batch_content, chunk.meta)
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                    current_batch = []

    def finish(self):
        self.queue.put("[END]")
