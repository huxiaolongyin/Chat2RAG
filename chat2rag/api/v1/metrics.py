from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from tortoise.expressions import Q

from chat2rag.responses import Success
from chat2rag.schemas.common import Current, Size
from chat2rag.services.metric_service import MetricService

router = APIRouter()

metric_service = MetricService()


@router.get("/", summary="获取对话历史")
@router.get("/list", summary="获取对话历史")
async def get_metrics_list(
    current: Current = 1,
    size: Size = 10,
    start_time: Optional[str] = Query("2023-01-01", description="开始时间", alias="startTime"),
    end_time: Optional[str] = Query("2099-01-01", description="结束时间", alias="endTime"),
    collection: Optional[str] = Query(None, description="知识库"),
):
    q = Q()
    if start_time:
        start_time_value = start_time if not hasattr(start_time, "default") else start_time.default
        start_datetime = datetime.strptime(start_time_value, "%Y-%m-%d") if start_time_value else datetime(2023, 1, 1)
        q &= Q(create_time__gte=start_datetime)
    if end_time:
        end_time_value = end_time if not hasattr(end_time, "default") else end_time.default
        end_datetime = (
            datetime.strptime(end_time_value, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            if end_time_value
            else datetime(2026, 1, 1, 23, 59, 59)
        )
        q &= Q(create_time__lt=end_datetime)
    if collection:
        q &= Q(collections__icontains=collection)

    total, metrics = await metric_service.get_list(page=current, page_size=size, search=q, order=["-create_time"])
    data = []
    for metric in metrics:
        parse_content = {
            "create_time": metric.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "collections": metric.collections,
            "question": metric.question,
            "answer": metric.answer,
            "first_response_ms": metric.first_response_ms,
            "total_ms": metric.total_ms,
            "model": metric.model,
            "chat_id": metric.chat_id,
            "chat_rounds": metric.chat_rounds,
            "tools": metric.tools,
            "precision_mode": metric.precision_mode,
            "prompt": metric.prompt,
        }
        data.append(parse_content)

    return Success(data=data, total=total, current=current, size=size)
