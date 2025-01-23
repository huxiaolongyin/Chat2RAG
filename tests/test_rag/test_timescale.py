from datetime import datetime

import pytest

from rag_core.database import RAGPipelineMetrics, TimescaleDB


@pytest.fixture
def db():
    db = TimescaleDB()
    db._init_timescale_hypertable()
    return db


@pytest.fixture
def sample_metric():
    return RAGPipelineMetrics(
        time=datetime.now(),
        chat_id="test_chat_123",
        question="What is RAG?",
        answer="RAG is Retrieval Augmented Generation",
        document_ms=50.5,
        function_ms=20.3,
        rag_response_ms=150.8,
        total_ms=221.6,
        document_count=3,
        question_tokens=10,
        status="success",
    )


def test_insert_and_query(db, sample_metric):
    db.insert_metric(sample_metric)

    results = db.get_metrics(chat_id="test_chat_123", hours=24)
    assert len(results) > 0

    result = results[0]
    assert result.chat_id == "test_chat_123"
    assert result.question == "What is RAG?"
    assert result.document_count == 3
    assert result.status == "success"
