from datetime import datetime
from typing import Any, Dict

from .base import BaseSchema


class MetricCreate(BaseSchema):
    message_id: str
    question: str = ""
    image: str | None = None
    chat_id: str | None = None
    chat_rounds: int | None = None
    answer: str = ""
    model: str | None = None
    prompt: str | None = None
    tools: str | None = None
    collections: str | None = None
    retrieval_params: Dict[str, Any] | None = None
    document_count: int = 0
    document_ms: float = 0.0
    tool_ms: float = 0.0
    first_response_ms: float | None = None
    total_ms: float | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    tool_result: Dict[str, Any] | None = None
    error_message: str | None = None
    precision_mode: bool | None = False
    extra_params: Dict[str, Any] | None = None
    meta_data: Dict[str, Any] | None = None
    execute_tools: str | None = None
    expression: Any | None = None
    action: Any | None = None
    create_time: datetime = datetime.now()


class MetricUpdate(BaseSchema):
    answer: str | None = None
    document_count: int | None = None
    document_ms: float | None = None
    tool_ms: float | None = None
    first_response_ms: float | None = None
    total_ms: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    tool_result: Dict[str, Any] | None = None
    error_message: str | None = None
    meta_data: Dict[str, Any] | None = None
