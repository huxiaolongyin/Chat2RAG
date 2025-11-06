from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class MetricCreate(BaseModel):
    message_id: str
    question: str
    chat_id: Optional[str] = None
    chat_rounds: Optional[int] = None
    answer: Optional[str] = None
    model: Optional[str] = None
    prompt: Optional[str] = None
    tools: Optional[str] = None
    collections: Optional[str] = None
    retrieval_params: Optional[Dict[str, Any]] = None
    document_count: int = 0
    document_ms: float = 0.0
    tool_ms: float = 0.0
    first_response_ms: Optional[float] = None
    total_ms: Optional[float] = None
    input_tokens: int = 0
    output_tokens: int = 0
    tool_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    precision_mode: Optional[bool] = False
    extra_params: Optional[Dict[str, Any]] = None
    meta_data: Optional[Dict[str, Any]] = None
    execute_tools: Optional[str] = None
    create_time: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MetricUpdate(BaseModel):
    answer: Optional[str] = None
    document_count: Optional[int] = None
    document_ms: Optional[float] = None
    tool_ms: Optional[float] = None
    first_response_ms: Optional[float] = None
    total_ms: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    tool_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
