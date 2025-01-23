from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from rag_core.database.database import SessionLocal
from rag_core.database.models import RAGPipelineMetrics
from rag_core.logging import logger


class TimescaleDB:
    def __init__(self):
        self.Session = SessionLocal
        self._init_timescale_hypertable()

    def _init_timescale_hypertable(self):
        with self.Session() as session:
            session.execute(
                text(
                    "SELECT create_hypertable('rag_pipeline_metrics', 'time', if_not_exists => TRUE)"
                )
            )
            session.commit()

    def insert_metric(self, metric: RAGPipelineMetrics):
        with self.Session() as session:
            try:
                session.add(metric)
                session.commit()
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Failed to insert metric: {e}")
                raise

    def get_metrics(
        self, chat_id: Optional[str] = None, hours: int = 24
    ) -> List[RAGPipelineMetrics]:
        with self.Session() as session:
            query = session.query(RAGPipelineMetrics)

            if chat_id:
                query = query.filter(RAGPipelineMetrics.chat_id == chat_id)

            query = query.filter(
                RAGPipelineMetrics.time > text("NOW() - INTERVAL ':hours hours'")
            ).params(hours=hours)

            return query.order_by(RAGPipelineMetrics.time.desc()).all()

    def batch_insert_metrics(self, metrics: List[RAGPipelineMetrics]):
        with self.Session() as session:
            try:
                session.bulk_save_objects(metrics)
                session.commit()
            except SQLAlchemyError as e:
                session.rollback()
                logger.error(f"Failed to batch insert metrics: {e}")
                raise

    def check_connection(self):
        """
        Connection health check
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
