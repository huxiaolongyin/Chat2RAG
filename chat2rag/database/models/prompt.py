from sqlalchemy import Column, Integer, String

from chat2rag.database.connection import Base
from chat2rag.database.models.base import BaseModel


class Prompt(Base, BaseModel):
    """提示词表"""

    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True)
    prompt_name = Column(String)
    prompt_intro = Column(String)
    prompt_text = Column(String)
