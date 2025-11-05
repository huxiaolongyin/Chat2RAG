from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PromptBase(BaseModel):
    prompt_name: str = Field(..., alias="promptName")
    prompt_desc: str = Field(..., alias="promptDesc")
    prompt_text: str = Field(..., alias="promptText")


class PromptCreate(PromptBase):

    @field_validator("prompt_name", "prompt_desc", "prompt_text")
    @classmethod
    def not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("不能为空")
        return v


class PromptUpdate(PromptBase):
    prompt_name: Optional[str] = Field(..., alias="promptName")
    prompt_desc: Optional[str] = Field(None, alias="promptDesc")
    prompt_text: Optional[str] = Field(None, alias="promptText")
