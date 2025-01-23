from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class RAGPipelineMetrics(Base):
    __tablename__ = "rag_pipeline_metrics"

    time = Column(DateTime(timezone=True), primary_key=True)
    chat_id = Column(String)
    question = Column(String, nullable=False)
    answer = Column(String)
    document_ms = Column(Float)
    function_ms = Column(Float)
    rag_response_ms = Column(Float)
    total_ms = Column(Float)
    document_count = Column(Integer)
    question_tokens = Column(Integer)
    status = Column(String)


class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True)
    prompt_name = Column(String)
    prompt_text = Column(String)
    create_time = Column(DateTime(timezone=True), default=datetime.now())
    update_time = Column(
        DateTime(timezone=True), default=datetime.now(), onupdate=datetime.now()
    )

    def to_dict(self):
        return {
            "id": self.id,
            "prompt_name": self.prompt_name,
            "prompt_text": self.prompt_text,
            "create_time": self.create_time.isoformat() if self.create_time else None,
            "update_time": self.update_time.isoformat() if self.update_time else None,
        }
