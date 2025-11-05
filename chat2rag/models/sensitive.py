from tortoise import fields

from .base import BaseModel, TimestampMixin


class SensitiveWords(BaseModel, TimestampMixin):
    """敏感词"""

    id = fields.IntField(primary_key=True)
    word = fields.CharField(
        max_length=100, unique=True, db_index=True, description="敏感词内容"
    )
    category = fields.ForeignKeyField(
        "app_system.SensitivedCategory",
        related_name="sensitive_words",
        null=True,
        description="分类ID",
    )
    level = fields.IntField(default=1, description="敏感级别(1-低 2-中 3-高)")
    description = fields.CharField(max_length=255, null=True, description="描述信息")
    is_active = fields.BooleanField(default=True, description="是否启用")

    class Meta:
        table = "sensitive_words"


class SensitivedCategory(BaseModel, TimestampMixin):
    """敏感词分类表"""

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=50, unique=True, description="分类名称")
    description = fields.CharField(max_length=255, null=True, description="描述信息")

    class Meta:
        table = "sensitive_categories"
