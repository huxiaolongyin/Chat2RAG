from datetime import datetime

from pydantic import BaseModel, Field


class PromptBase(BaseModel):
    prompt_name: str = Field(..., alias="promptName")
    prompt_intro: str = Field(..., alias="promptIntro")
    prompt_text: str = Field(..., alias="promptText")


class PromptCreate(PromptBase):
    pass


class PromptResponse(PromptBase):
    id: int
    create_time: datetime
    update_time: datetime

    class Config:
        from_attributes = True
