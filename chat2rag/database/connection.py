from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from chat2rag.config import CONFIG
from chat2rag.logger import get_logger

logger = get_logger(__name__)

# 创建引擎
engine = create_engine(
    CONFIG.DATABASE_URL,
    pool_size=5,  # The number of connections maintained by the connection pool
    max_overflow=10,  # The maximum number of connections that can be created beyond the pool size
    pool_timeout=30,  # The timeout for acquiring a connection from the pool
    pool_recycle=3600,  # The time at which a connection is reset, preventing the connection from being disconnected by the database
    echo=False,  # Setting it to True allows you to view the SQL statement
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        db.close()


from contextlib import contextmanager


# 上下文管理器版本 - 用于with语句
@contextmanager
def db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        db.close()


def init_db():
    """初始化数据库"""
    from chat2rag.database.models.flow_data import FlowData
    from chat2rag.database.models.metric import Metric
    from chat2rag.database.models.prompt import Prompt

    Base.metadata.create_all(engine)
