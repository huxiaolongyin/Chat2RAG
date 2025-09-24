from sqlalchemy import JSON, Column, ForeignKey, Integer, String, UniqueConstraint

from chat2rag.database.connection import Base
from chat2rag.database.models.base import BaseModel


class FlowData(Base, BaseModel):
    """流程数据 - 主记录"""

    __tablename__ = "flow_data"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    desc = Column(String)
    current_version = Column(Integer, default=1)  # 当前最新版本
    flow_json = Column(JSON)


# # 历史表：每个保存动作一个版本
# class FlowDataHistory(Base, BaseModel):
#     """流程数据历史版本"""
#     __tablename__ = "flow_data_history"
#     id = Column(Integer, primary_key=True)
#     flow_data_id = Column(Integer, ForeignKey("flow_data.id"), nullable=False)
#     version = Column(Integer, nullable=False)
#     flow_json = Column(JSON, nullable=False)

#     __table_args__ = (
#         UniqueConstraint('flow_data_id', 'version'),
#     )
