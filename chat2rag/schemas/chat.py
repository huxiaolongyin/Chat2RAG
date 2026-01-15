import json
from datetime import datetime
from typing import Any

from pydantic import Field, field_validator, model_validator

from chat2rag.config import CONFIG
from chat2rag.core.enums import ProcessType
from chat2rag.dataclass.strategy import StrategyRequest

from .base import BaseSchema


class Audio(BaseSchema):
    voice: str
    format: str


class QueryContent(BaseSchema):
    text: str = ""
    image: str = ""
    video: str = ""
    audio: str = ""

    @model_validator(mode="after")
    def check_at_least_one_content(self):
        if not any([self.text, self.image, self.video, self.audio]):
            raise ValueError("至少需要提供一种内容类型（text/image/video/audio）")
        return self


class ChatQueryParams(BaseSchema):
    """旧版ChatV1 请求参数模型"""

    collection_name: str | None = Field(None, description="知识库名称")
    query: str = Field(..., description="查询内容")
    top_k: int = Field(default=5, ge=0, le=30, description="返回数量")
    score_threshold: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        description="文档匹配分数阈值",
    )
    precision_mode: int = Field(default=0, description="是否使用精确模式")
    chat_id: str | None = Field(None, description="聊天的标识")
    chat_rounds: int = Field(default=1, ge=0, le=30, description="聊天轮数")
    batch_or_stream: ProcessType = (Field(ProcessType.BATCH),)
    prompt_name: str = Field("默认", description="提示词名称选择")
    generator_model: str = Field(default=CONFIG.CHAT_V1_DEFAULT_MODELS["generator"], description="生成模型")
    generation_kwargs: str = Field(default="{}", description="生成参数")
    tool_list: str = Field(default="[]", description="工具列表，JSON字符串格式")

    def to_strategy_request(self) -> StrategyRequest:
        """转换为策略请求模型（V1）"""
        return StrategyRequest(
            content=QueryContent(text=self.query),
            chat_id=self.chat_id,
            precision_mode=self.precision_mode,
            collections=[self.collection_name] if self.collection_name else [],
            top_k=self.top_k,
            score_threshold=self.score_threshold,
            chat_rounds=self.chat_rounds,
            prompt_name=self.prompt_name,
            model=self.generator_model,
            generation_kwargs=self.generation_kwargs,
            tools=self.tool_list,
            batch_or_stream=self.batch_or_stream,
        )

    @field_validator("tool_list", mode="after")
    @classmethod
    def parse_tool_list(cls, v: str) -> list:
        """将 tool_list 从 JSON 字符串转换为列表"""
        if isinstance(v, list):
            return v
        try:
            parsed = json.loads(v)
            if not isinstance(parsed, list):
                raise ValueError("tool_list must be a JSON array")
            return parsed
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format for tool_list: {e}")


class ChatRequest(BaseSchema):
    """
    Request parameter model for chat
    """

    model: str = Field(default=CONFIG.MODEL, description="模型名称，非必填，使用默认配置模型")
    generation_kwargs: dict = Field(default=CONFIG.GENERATION_KWARGS, description="模型采样参数，非必填，使用默认参数")
    prompt_name: str = Field(default=CONFIG.PROMPT_NAME, description=f"角色名称，非必填，默认: {CONFIG.PROMPT_NAME}")
    collections: list = Field(default=[], description="知识库名称，非必填，支持多个，空值为不进行知识库检索")
    score_threshold: float = Field(
        default=CONFIG.SCORE_THRESHOLD,
        ge=0.0,
        le=1.0,
        description=f"文档匹配分数阈值，非必填，范围0-1.0，默认: {CONFIG.SCORE_THRESHOLD}",
    )
    top_k: int = Field(default=CONFIG.TOP_K, ge=0, le=30, description=f"  : {CONFIG.TOP_K}")
    batch_or_stream: ProcessType = Field(
        default=CONFIG.BATCH_OR_STREAM, description=f"接口的返回形式，batch 或 stream，默认: {CONFIG.BATCH_OR_STREAM}"
    )
    precision_mode: int = Field(
        default=CONFIG.PRECISION_MODE, description=f"精确模式，非必填，0-不使用，1-使用，默认: {CONFIG.PRECISION_MODE}"
    )
    tools: list = Field(default=CONFIG.TOOLS, description="工具列表，非必填，默认为空")
    flows: list = Field(default=[], description="流程列表，非必填，选择调用的流程，默认为空")
    content: QueryContent = Field(..., description="交互内容，必填，支持类型：text、image、video、audio")
    chat_id: str | None = Field(None, description="会话标识，非必填，用于处理多轮聊天会话")
    chat_rounds: int = Field(
        default=CONFIG.CHAT_ROUNDS,
        ge=0,
        le=30,
        description=f"会话轮数，非必填，多轮对话的轮数，0-30，默认: {CONFIG.CHAT_ROUNDS}",
    )
    modalities: list = Field(
        default=CONFIG.MODALITIES,
        description=f'支持输出的模态，如文本、图像等，非必填，支持["text","audio"]、["text"]，默认: {CONFIG.MODALITIES}',
    )
    audio: Audio = Field(default={}, description="声音输出配置, 非必填")
    extra_params: dict = Field(default={}, description="额外参数，非必填，传入prompt提示词的参数")

    @field_validator("tools", mode="after")
    def parse_tool(cls, v: list) -> list:
        try:
            return [s.strip("'") for s in v]
        except Exception as e:
            return v

    @field_validator("collections", mode="after")
    def parse_collections(cls, v: list) -> list:
        if not v or not v[0]:
            return ["None"]
        return v

    @field_validator("prompt_name", mode="after")
    def parse_prompt_name(cls, v: list) -> list:
        if not v:
            return "默认"
        return v


class StreamChunkV1(BaseSchema):
    object: str = Field("message", description="数据类型", examples=["message"])
    content: str = Field(..., description="响应消息内容", examples=["你好！有什么可以帮您的吗？"])
    model: str = Field("None", description="调用模型名称", examples=["qwen-32b"])
    status: int = Field(..., description="回复状态，0: 准备回复、1:回复开始、2:回复结束", examples=[0])
    document_count: int = Field(..., description="文档的检索数量", examples=[5])
    create_time: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message_id: str = Field(..., description="响应消息的唯一ID", examples=["9d0cc3bc43d845ef"])


class ContentSchema(BaseSchema):
    text: str = Field("", description="文本内容", examples=["这是回复的文本内容"])
    image: str = Field("", description="图片内容或URL", examples=["image_url_or_base64"])


class BehaviorSchema(BaseSchema):
    emoji: str = Field("", description="表情", examples=["微笑"])
    action: str = Field("", description="行为动作", examples=["抬手"])


class ToolSchema(BaseSchema):
    tool_name: str = Field("", description="工具名称", examples=["maps_weather"])
    tool_type: str = Field("", description="工具类型")
    arguments: dict = Field({}, description="工具参数")
    tool_result: Any = Field("", description="工具结果")


class StreamChunkV2(BaseSchema):
    object: str = Field("message", description="数据类型", examples=["message"])
    input: dict = Field({}, description="用户输入内容", examples=["你好，请帮我查询天气"])
    content: ContentSchema = Field(..., description="响应内容，包含文本和图片")
    model: str = Field("None", description="调用模型名称", examples=["qwen-32b"])
    status: int = Field(..., description="回复状态，0: 准备回复、1:回复开始、2:回复结束", examples=[0])
    behavior: BehaviorSchema = Field(..., description="行为数据，包含表情和动作")
    tool: ToolSchema = Field(..., description="工具调用内容")
    link: str = Field("", description="相关链接信息")
    document_count: int = Field(..., description="文档的检索数量", examples=[5])
    create_time: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message_id: str = Field(..., description="响应消息的唯一ID", examples=["9d0cc3bc43d845ef"])

    def to_stream_chunk_v1(self):
        return StreamChunkV1(
            content=self.content.text,
            model=self.model,
            status=self.status,
            document_count=self.document_count,
            message_id=self.message_id,
        )
