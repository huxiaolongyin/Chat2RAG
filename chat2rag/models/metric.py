from tortoise import fields

from .base import BaseModel, TimestampMixin


class Metric(BaseModel, TimestampMixin):
    """聊天性能指标表 - 针对PostgreSQL时序数据库优化"""

    # 主键保持不变，但确保是UUID格式
    message_id = fields.CharField(
        max_length=36, primary_key=True, description="消息唯一标识符"
    )

    # 会话相关字段 - 聚合查询的重要维度
    chat_id = fields.CharField(max_length=36, null=True, description="聊天会话的标识符")
    chat_rounds = fields.IntField(null=True, description="所属会话轮次")

    # 用户输入和系统响应
    question = fields.TextField(description="用户提问内容")
    image = fields.TextField(null=True, description="用户输入的图片")
    answer = fields.TextField(null=True, description="系统回答内容")
    answer_image = fields.TextField(null=True, description="回复中的图片")
    answer_video = fields.TextField(null=True, description="回复中的视频")

    # 表情和动作
    expression = fields.ForeignKeyField(
        "app_system.RobotExpression",
        related_name="metrics",
        null=True,
        description="表情",
    )
    action = fields.ForeignKeyField(
        "app_system.RobotAction", related_name="metrics", null=True, description="动作"
    )

    # 模型和配置参数 - 可能需要分组统计的字段
    model = fields.CharField(max_length=100, null=True, description="使用的模型名称")
    prompt = fields.CharField(max_length=100, null=True, description="使用的prompt名称")

    # 工具和知识库参数 - 常用于分析的字段
    tools = fields.CharField(
        max_length=255, null=True, description="使用的工具名称，逗号分隔"
    )
    collections = fields.CharField(
        max_length=255, null=True, description="使用的知识库名称，逗号分隔"
    )

    # 检索参数 - 可合并为JSON字段减少列数
    retrieval_params = fields.JSONField(
        null=True, description="检索相关参数，包含top_k、score_threshold等"
    )

    # 执行工具
    execute_tools = fields.CharField(
        max_length=255, null=True, description="使用的工具名称，逗号分隔"
    )

    # 性能指标 - 时序数据的核心指标
    document_count = fields.IntField(default=0, description="检索的文档数量")
    document_ms = fields.FloatField(default=0.0, description="文档检索耗时(毫秒)")
    tool_ms = fields.FloatField(default=0.0, description="工具调用耗时(毫秒)")
    first_response_ms = fields.FloatField(null=True, description="首次响应耗时(毫秒)")
    total_ms = fields.FloatField(null=True, description="总响应耗时(毫秒)")

    # Token计数
    input_tokens = fields.IntField(default=0, description="输入token数量")
    output_tokens = fields.IntField(default=0, description="输出token数量")

    # 结果和错误信息
    tool_arguments = fields.JSONField(null=True, description="工具调用参数")
    tool_result = fields.JSONField(null=True, description="工具调用结果")
    error_message = fields.TextField(null=True, description="错误信息(如果有)")

    # 其他配置和元数据
    precision_mode = fields.BooleanField(
        null=True, default=False, description="是否使用精确模式"
    )
    extra_params = fields.JSONField(null=True, description="额外参数")
    meta_data = fields.JSONField(null=True, description="额外元数据")
    source = fields.JSONField(null=True, description="信息来源")
    retrieval_documents = fields.JSONField(
        null=True, description="检索文档，按知识库分组"
    )

    # 基础字段（来自 BaseModel）
    create_time = fields.DatetimeField(auto_now_add=True)
    update_time = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "metrics"
        # Tortoise ORM 中的索引需要在数据库层面单独处理
        # 或者使用 raw SQL 创建 TimescaleDB hypertable
