from sqlalchemy import JSON, Boolean, Column, Float, Index, Integer, String, Text

from chat2rag.database.connection import Base
from chat2rag.database.models.base import BaseModel


class Metric(Base, BaseModel):
    """聊天性能指标表 - 针对PostgreSQL时序数据库优化"""

    __tablename__ = "metrics"

    # 主键保持不变，但确保是UUID格式
    message_id = Column(String(36), primary_key=True, comment="消息唯一标识符")

    # 会话相关字段 - 聚合查询的重要维度
    chat_id = Column(String(36), nullable=True, index=True, comment="聊天会话的标识符")
    chat_rounds = Column(Integer, nullable=True, comment="所属会话轮次")

    # 用户输入和系统响应
    question = Column(Text, nullable=False, comment="用户提问内容")
    answer = Column(Text, nullable=True, comment="系统回答内容")

    # 模型和配置参数 - 可能需要分组统计的字段
    model = Column(String(100), nullable=True, index=True, comment="使用的模型名称")
    prompt = Column(String(100), nullable=True, comment="使用的prompt名称")

    # 工具和知识库参数 - 常用于分析的字段
    tools = Column(String(255), nullable=True, comment="使用的工具名称，逗号分隔")
    collections = Column(
        String(255), nullable=True, comment="使用的知识库名称，逗号分隔"
    )

    # 检索参数 - 可合并为JSON字段减少列数
    retrieval_params = Column(
        JSON, nullable=True, comment="检索相关参数，包含top_k、score_threshold等"
    )

    # 性能指标 - 时序数据的核心指标
    document_count = Column(Integer, default=0, comment="检索的文档数量")
    document_ms = Column(Float, default=0.0, comment="文档检索耗时(毫秒)")
    tool_ms = Column(Float, default=0.0, comment="工具调用耗时(毫秒)")
    first_response_ms = Column(Float, nullable=True, comment="首次响应耗时(毫秒)")
    total_ms = Column(Float, nullable=True, comment="总响应耗时(毫秒)")

    # Token计数
    input_tokens = Column(Integer, default=0, comment="输入token数量")
    output_tokens = Column(Integer, default=0, comment="输出token数量")

    # 结果和错误信息
    tool_result = Column(JSON, nullable=True, comment="工具调用结果")
    error_message = Column(Text, nullable=True, comment="错误信息(如果有)")

    # 其他配置和元数据
    precision_mode = Column(
        Boolean, nullable=True, default=False, comment="是否使用精确模式"
    )
    extra_params = Column(JSON, nullable=True, comment="额外参数")
    meta_data = Column(JSON, nullable=True, comment="额外元数据")

    # 添加针对时序数据库的索引和约束
    __table_args__ = (
        # 时序数据的主要查询模式：按时间范围+会话ID
        Index("idx_time_chat", "create_time", "chat_id"),
        # 性能分析常用：按模型+时间查询
        Index("idx_model_time", "model", "create_time"),
        # 可选：添加TimescaleDB的hypertable声明（需要在表创建后执行SQL）
        {"comment": "Chat metrics for performance monitoring"},
    )
