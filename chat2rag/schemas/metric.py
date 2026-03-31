from datetime import datetime
from typing import Any, Dict, List

from pydantic import Field

from .base import BaseSchema


class MetricBase(BaseSchema):
    create_time: datetime = datetime.now()
    collections: str | None = None
    question: str = ""
    image: str | None = None
    answer: str | None = ""
    answer_image: str | None = None
    answer_video: str | None = None
    first_response_ms: float | None = None
    total_ms: float | None = None
    model: str | None = None
    chat_id: str | None = None
    chat_rounds: int | None = None
    tools: str | None = None
    precision_mode: bool | None = False
    prompt: str | None = None
    source: List[Dict[str, str]] | None = None
    retrieval_documents: Dict[str, List[Dict[str, Any]]] | None = None
    input_tokens: int = 0
    output_tokens: int = 0


class MetricData(MetricBase):
    tool_arguments: Dict[str, Any] | None = None
    tool_result: Dict[str, Any] | None = None
    document_count: int = 0
    execute_tools: str | None = None


class MetricCreate(MetricBase):
    message_id: str
    question: str = ""
    image: str | None = None
    answer_image: str | None = None
    answer_video: str | None = None
    retrieval_params: Dict[str, Any] | None = None
    document_count: int = 0
    document_ms: float = 0.0
    tool_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    tool_arguments: Dict[str, Any] | None = None
    tool_result: Dict[str, Any] | None = None
    error_message: str | None = None
    extra_params: Dict[str, Any] | None = None
    meta_data: Dict[str, Any] | None = None
    execute_tools: str | None = None
    expression: Any | None = None
    action: Any | None = None


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


class HotQuestionPoint(BaseSchema):
    id: str = Field(..., description="ID", examples=["2edcf681-f8d2-5188-afd6-b94c79b87c41"])
    text: str = Field(..., description="相似问题", examples=["地铁咋走啊"])
    collection: str = Field(..., description="知识库/场景", examples=["北京朝阳站"])
    create_time: str = Field(..., description="创建时间", examples=["2025-09-28T15:21:15.911842+08:00"])
    update_time: str = Field(..., description="创建时间", examples=["2026-01-11T16:43:37.679929+08:00"])
    count: int


class HotQuestionData(BaseSchema):
    id: str = Field(..., description="ID", examples=["8c495fea-ca58-587a-8b83-d07eb7561be6"])
    representative_question: str = Field(..., description="热点问题中最具代表性的问题", examples=["地铁怎么走"])
    count: int = Field(..., description="热点问题出现的次数", examples=[57])
    cluster_size: int = Field(..., description="聚类的大小", examples=[8])
    create_time: str = Field(..., description="创建时间", examples=["2025-09-28T15:21:15.911842+08:00"])
    update_time: str = Field(..., description="创建时间", examples=["2026-01-11T16:43:37.679929+08:00"])
    similar_questions: List[HotQuestionPoint] = Field(..., description="相似问题列表")


class ChatSessionData(BaseSchema):
    chat_id: str = Field(..., description="会话ID")
    first_question: str = Field(..., description="首个问题作为会话标题")
    message_count: int = Field(..., description="消息数量")
    total_input_tokens: int = Field(default=0, description="总输入token数")
    total_output_tokens: int = Field(default=0, description="总输出token数")
    model: str | None = Field(None, description="使用的模型")
    collections: str | None = Field(None, description="使用的知识库")
    create_time: datetime = Field(..., description="创建时间")
    update_time: datetime = Field(..., description="最后更新时间")


class SessionStatsData(BaseSchema):
    chat_id: str = Field(..., description="会话ID")
    message_count: int = Field(..., description="消息数量")
    total_input_tokens: int = Field(default=0, description="总输入token数")
    total_output_tokens: int = Field(default=0, description="总输出token数")
    total_tokens: int = Field(default=0, description="总token数")
    avg_first_response_ms: float | None = Field(None, description="平均首字延迟(ms)")
    avg_total_ms: float | None = Field(None, description="平均总延迟(ms)")
    models_used: List[str] = Field(default_factory=list, description="使用的模型列表")
    collections_used: List[str] = Field(default_factory=list, description="使用的知识库列表")
