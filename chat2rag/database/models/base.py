# from datetime import datetime
import datetime

from sqlalchemy import Column, DateTime
from sqlalchemy.ext.declarative import declared_attr


class BaseModel(object):
    """所有模型的基类"""

    create_time = Column(
        DateTime,
        default=datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )
    update_time = Column(
        DateTime,
        default=datetime.datetime.now(datetime.timezone.utc),
        onupdate=datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    def to_dict(self):
        """将模型转换为字典"""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
