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
        result = {}
        for c in self.__table__.columns:
            value = getattr(self, c.name)
            # 处理datetime类型，转换为格式化的字符串
            if isinstance(value, datetime.datetime):
                result[c.name] = value.strftime("%Y-%m-%d %H:%M:%S")
            else:
                result[c.name] = value
        return result
