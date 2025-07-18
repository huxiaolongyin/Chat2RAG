from chat2rag.database.connection import db_session
from chat2rag.database.models.metric import Metric
from chat2rag.database.services.metric_service import MetricService

# 测试数据
test_metric = Metric(
    message_id="test_message_id",
    chat_id="test_chat_id",
    chat_rounds=1,
    question="test_question",
    answer="test_answer",
    model="test_model",
    prompt="test_prompt",
    tools="test_tools",
    collections="test_collections",
    retrieval_params={"top_k": 5, "score_threshold": 0.5},
    document_count=10,
    document_ms=100,
    tool_ms=200,
    first_response_ms=300,
    total_ms=400,
    input_tokens=500,
    output_tokens=600,
    tool_result={"result": "test_result"},
    error_message="test_error_message",
    precision_mode=False,
    extra_params={"param1": "value1"},
    meta_data={"key1": "value1"},
)
metric_service = MetricService()


def test_message_add():
    with db_session() as db:
        metric_service.create(db, test_metric)


test_message_add()
