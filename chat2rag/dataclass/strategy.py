from dataclasses import dataclass, field


@dataclass
class QueryContent:
    text: str = ""
    image: str = ""
    video: str = ""
    audio: str = ""


@dataclass
class StrategyRequest:
    """策略统一请求模型"""

    content: QueryContent
    chat_id: str | None = None
    precision_mode: int = 0
    collections: list[str] = field(default_factory=list)
    top_k: int = 5
    score_threshold: float = 0.65
    chat_rounds: int = 1
    prompt_name: str = "默认"
    model: str = ""
    generation_kwargs: dict = field(default_factory=dict)
    tools: list[str] = field(default_factory=list)
    flows: list = field(default_factory=list)
    extra_params: dict = field(default_factory=dict)
