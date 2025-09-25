from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from chat2rag.api.schema import Success
from chat2rag.database.connection import db_session
from chat2rag.database.services.metric_service import MetricService

router = APIRouter()

metric_service = MetricService()


@router.get("/list", summary="获取对话历史")
def get_metrics_list(
    current: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页数量"),
    start_time: Optional[str] = Query(
        "2023-01-01", description="开始时间", alias="startTime"
    ),
    end_time: Optional[str] = Query(
        "2026-01-01", description="结束时间", alias="endTime"
    ),
    collection: Optional[str] = Query(description="知识库"),
):
    """获取指标列表，支持分页、搜索和排序"""
    current_value = current if not hasattr(current, "default") else current.default
    size_value = size if not hasattr(size, "default") else size.default
    start_time_value = (
        start_time if not hasattr(start_time, "default") else start_time.default
    )
    end_time_value = end_time if not hasattr(end_time, "default") else end_time.default
    collection_value = (
        collection if not hasattr(collection, "default") else collection.default
    )

    # 将字符串转换为datetime对象
    start_datetime = (
        datetime.strptime(start_time_value, "%Y-%m-%d")
        if start_time_value
        else datetime(2023, 1, 1)
    )
    end_datetime = (
        datetime.strptime(end_time_value, "%Y-%m-%d")
        if end_time_value
        else datetime(2026, 1, 1)
    )
    with db_session() as db:
        metrics, total = metric_service.get_metrics_by_time_range(
            db=db,
            start_time=start_datetime,
            end_time=end_datetime,
            collection=collection_value,
            page=current_value,
            page_size=size_value,
        )
        data = []
        for metric in metrics:
            parse_content = {
                "create_time": metric.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                "model": metric.model,
                "question": metric.question,
                "answer": metric.answer,
                "first_response_ms": metric.first_response_ms,
                "total_ms": metric.total_ms,
            }
            data.append(parse_content)

    return Success(data=data, total=total, current=current, size=size)
