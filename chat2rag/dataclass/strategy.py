from dataclasses import dataclass
from typing import Optional


@dataclass
class StrategyRequest:
    """策略统一请求模型"""

    content: dict
    chat_id: Optional[str] = None
    precision_mode: int = 0
    collections: list[str] = None
    top_k: int = 5
    score_threshold: float = 0.65
    chat_rounds: int = 1
    prompt_name: str = "默认"
    model: str = ""
    generation_kwargs: dict = None
    tools: list = None
    flows: list = None
    extra_params: dict = None
    intention_model: str = ""

    def __post_init__(self):
        if self.collections is None:
            self.collections = []
        if self.generation_kwargs is None:
            self.generation_kwargs = {}
        if self.tools is None:
            self.tools = []
        if self.flows is None:
            self.flows = []
        if self.extra_params is None:
            self.extra_params = {}
