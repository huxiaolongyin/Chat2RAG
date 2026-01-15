import random

from tortoise import fields

from .base import BaseModel, TimestampMixin


class Category(BaseModel, TimestampMixin):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=64, unique=True)
    model_name = fields.CharField(max_length=128)
    description = fields.TextField(null=True)  # 备注或描述

    transition_phrases: fields.ReverseRelation["TransitionPhrase"]

    async def get_random_transition_phrase(self) -> str:
        phrases = await self.transition_phrases.all()
        if phrases:
            return random.choice(phrases).phrase
        return ""

    class Meta:
        table = "category"


class TransitionPhrase(BaseModel, TimestampMixin):
    id = fields.IntField(primary_key=True)
    category_model = fields.ForeignKeyField(
        "app_system.Category",
        related_name="transition_phrases",
        on_delete=fields.CASCADE,
    )
    phrase = fields.CharField(max_length=256)

    class Meta:
        table = "transition_phrases"
