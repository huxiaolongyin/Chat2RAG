from tortoise import fields

from .base import BaseModel, TimestampMixin


class Prompt(BaseModel, TimestampMixin):
    """主表，提示词基础信息"""

    id = fields.IntField(pk=True)
    prompt_name = fields.CharField(max_length=255, unique=True)
    current_version = fields.IntField(null=True)

    class Meta:
        table = "prompts"


class PromptVersion(BaseModel, TimestampMixin):
    """版本表，存每个提示词的版本细节"""

    id = fields.IntField(pk=True)
    prompt = fields.ForeignKeyField("app_system.Prompt", related_name="versions")
    prompt_desc = fields.TextField(null=True)
    prompt_text = fields.TextField()
    version = fields.IntField()

    class Meta:
        table = "prompt_versions"
        unique_together = (("prompt", "version"),)
