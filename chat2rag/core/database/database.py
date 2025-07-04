from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from chat2rag.config import CONFIG

engine = create_engine(
    CONFIG.DATABASE_URL,
    pool_size=5,  # The number of connections maintained by the connection pool
    max_overflow=10,  # The maximum number of connections that can be created beyond the pool size
    pool_timeout=30,  # The timeout for acquiring a connection from the pool
    pool_recycle=3600,  # The time at which a connection is reset, preventing the connection from being disconnected by the database
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def create_all_tables():
    Base.metadata.create_all(engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
