from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from rag_core.config import CONFIG

engine = create_engine(
    CONFIG.DATABASE_URL,
    pool_size=5,  # 连接池保持的连接数
    max_overflow=10,  # 超过pool_size后最多可以创建的连接数
    pool_timeout=30,  # 获取连接的超时时间
    pool_recycle=3600,  # 连接重置时间，防止连接被数据库断开
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def create_all_tables():
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
