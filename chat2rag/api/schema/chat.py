from typing import Optional

from pydantic import BaseModel, Field, field_validator

from chat2rag.config import CONFIG
from chat2rag.enums import ProcessType


class Audio(BaseModel):
    voice: str
    format: str


class ChatRequest(BaseModel):
    """
    Request parameter model for chat
    """

    model: str = Field(
        default=CONFIG.MODEL,
        description="模型名称，非必填，使用默认配置模型",
    )
    generation_kwargs: dict = Field(
        default=CONFIG.GENERATION_KWARGS,
        alias="generationKwargs",
        description="模型采样参数，非必填，使用默认参数",
    )
    prompt_name: str = Field(
        default=CONFIG.PROMPT_NAME,
        alias="promptName",
        description=f"角色名称，非必填，默认: {CONFIG.PROMPT_NAME}",
    )
    collections: Optional[list] = Field(
        default=[],
        description="知识库名称，非必填，支持多个，空值为不进行知识库检索",
    )
    score_threshold: float = Field(
        default=CONFIG.SCORE_THRESHOLD,
        ge=0.0,
        le=1.0,
        alias="scoreThreshold",
        description=f"文档匹配分数阈值，非必填，范围0-1.0，默认: {CONFIG.SCORE_THRESHOLD}",
    )
    top_k: int = Field(
        default=CONFIG.TOP_K,
        ge=0,
        le=30,
        alias="topK",
        description=f"  : {CONFIG.TOP_K}",
    )
    batch_or_stream: ProcessType = Field(
        default=CONFIG.BATCH_OR_STREAM,
        alias="batchOrStream",
        description=f"接口的返回形式，batch 或 stream，默认: {CONFIG.BATCH_OR_STREAM}",
    )
    precision_mode: int = Field(
        default=CONFIG.PRECISION_MODE,
        alias="precisionMode",
        description=f"精确模式，非必填，0-不使用，1-使用，默认: {CONFIG.PRECISION_MODE}",
    )
    tools: Optional[list] = Field(
        default=CONFIG.TOOLS,
        description="工具列表，非必填，默认为空",
    )
    flows: Optional[list] = Field(
        default=[], description="流程列表，非必填，选择调用的流程，默认为空"
    )
    content: dict = Field(
        default={"text": ""},
        description="交互内容，必填，支持类型：text、image、video、audio",
    )
    chat_id: Optional[str] = Field(
        None,
        alias="chatId",
        description="会话标识，非必填，用于处理多轮聊天会话",
    )
    chat_rounds: int = Field(
        default=CONFIG.CHAT_ROUNDS,
        ge=0,
        le=30,
        alias="chatRounds",
        description=f"会话轮数，非必填，多轮对话的轮数，0-30，默认: {CONFIG.CHAT_ROUNDS}",
    )
    modalities: list = Field(
        default=CONFIG.MODALITIES,
        description=f'支持输出的模态，如文本、图像等，非必填，支持["text","audio"]、["text"]，默认: {CONFIG.MODALITIES}',
    )
    audio: Audio = Field(default={}, description="声音输出配置, 非必填")
    extra_params: dict = Field(
        default={},
        alias="extraParams",
        description="额外参数，非必填，传入prompt提示词的参数",
    )

    class Config:
        populate_by_name = True

    # @field_validator("content", mode="after")
    # def parse_content(cls, content: List[Dict[str, Any]]) -> Dict[str, Any]:
    #     text_parts = []
    #     images = []

    #     for item in content:
    #         if isinstance(item, dict):
    #             if item.get("text"):
    #                 text_parts.append(item["text"])
    #             if item.get("image"):
    #                 images.append(item["image"])

    #     return {
    #         "text": "\n".join(text_parts),  # 合并所有文本段落
    #         "images": images,  # 保留图片列表
    #     }

    @field_validator("model", mode="after")
    def parse_model(cls, v: str) -> str:
        for model in CONFIG.MODEL_LIST:
            if model["name"] == v:
                return model["id"]
        return v
