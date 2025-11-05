import ast
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from chat2rag.config import CONFIG
from chat2rag.dataclass.strategy import StrategyRequest
from chat2rag.enums import ProcessType


class Audio(BaseModel):
    voice: str
    format: str


class ChatQueryParams(BaseModel):
    """旧版ChatV1 请求参数模型"""

    collection_name: Optional[str] = Field(
        None, alias="collectionName", description="知识库名称"
    )
    query: str = Field(..., description="查询内容")
    top_k: int = Field(default=5, ge=0, le=30, alias="topK", description="返回数量")
    score_threshold: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        alias="scoreThreshold",
        description="文档匹配分数阈值",
    )
    precision_mode: int = Field(
        default=0, alias="precisionMode", description="是否使用精确模式"
    )
    chat_id: Optional[str] = Field(None, alias="chatId", description="聊天的标识")
    chat_rounds: int = Field(
        default=1, ge=0, le=30, alias="chatRounds", description="聊天轮数"
    )
    prompt_name: str = Field("默认", alias="promptName", description="提示词名称选择")
    intention_model: str = Field(
        default=CONFIG.DEFAULT_MODELS["intention"],
        alias="intentionModel",
        description="意图模型",
    )
    generator_model: str = Field(
        default=CONFIG.DEFAULT_MODELS["generator"],
        alias="generatorModel",
        description="生成模型",
    )
    generation_kwargs: str = Field(
        default="{}",
        alias="generationKwargs",
        description="生成参数",
    )
    tool_list: List[str] = Field(default=[], alias="toolList", description="工具列表")

    model_config = ConfigDict(populate_by_name=True)
    # class Config:
    #     populate_by_name = True

    @field_validator("generator_model", mode="after")
    def parse_generator_model(cls, model):
        if model in CONFIG.MODEL_MAP:
            return CONFIG.MODEL_MAP[model]
        elif model in CONFIG.VALID_MODEL_VALUES:
            return model
        else:
            return CONFIG.DEFAULT_MODEL

    @field_validator("intention_model", mode="after")
    def parse_intention_model(cls, model):
        if model in CONFIG.MODEL_MAP:
            return CONFIG.MODEL_MAP[model]
        elif model in CONFIG.VALID_MODEL_VALUES:
            return model
        else:
            return CONFIG.DEFAULT_MODEL

    @field_validator("generation_kwargs", mode="after")
    def parse_generation_kwargs(cls, generation_kwargs, info):
        # Start with the default config
        merged_kwargs = dict(CONFIG.GENERATION_KWARGS)

        # 获取模型 id 或名称
        model_id_or_name = info.data.get("generator_model")
        if model_id_or_name:
            # Find matching model in CONFIG.MODEL_LIST
            for model_entry in CONFIG.MODEL_LIST:
                if (
                    model_entry.get("id") == model_id_or_name
                    or model_entry.get("name") == model_id_or_name
                ):
                    model_gen_kwargs = model_entry.get("generation_kwargs")
                    if model_gen_kwargs and isinstance(model_gen_kwargs, dict):
                        merged_kwargs.update(model_gen_kwargs)
                    break

        # If user provided non-empty and non-"{}" string, parse and update
        if generation_kwargs and generation_kwargs != "{}":
            try:
                user_kwargs = ast.literal_eval(generation_kwargs)
                if not isinstance(user_kwargs, dict):
                    raise ValueError("generation_kwargs must be a dictionary string.")
                merged_kwargs.update(user_kwargs)
            except (ValueError, SyntaxError) as e:
                raise ValueError(f"Invalid generation_kwargs format: {e}")

        return merged_kwargs

    def to_strategy_request(self) -> StrategyRequest:
        """转换为策略请求模型（V1）"""
        return StrategyRequest(
            content={"text": self.query},
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
            intention_model=self.intention_model,
        )


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

    model_config = ConfigDict(populate_by_name=True)
    # class Config:
    #     populate_by_name = True

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
        if not v:
            return CONFIG.MODEL
        for model in CONFIG.MODEL_LIST:
            if model["name"] == v:
                return model["id"]
        return v

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
