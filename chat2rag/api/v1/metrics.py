from datetime import datetime
from typing import List

from fastapi import APIRouter, Query
from tortoise.expressions import Q

from chat2rag.schemas.base import BaseResponse, PaginatedResponse
from chat2rag.schemas.common import Current
from chat2rag.schemas.metric import HotQuestionData, MetricData
from chat2rag.services.metric_service import metric_service
from chat2rag.services.question_analyzer import question_analyzer

router = APIRouter()


@router.get("", response_model=PaginatedResponse[MetricData], summary="获取对话历史")
@router.get("/list", response_model=PaginatedResponse[MetricData], summary="获取对话历史")
async def get_metrics_list(
    current: Current = 1,
    size: int = Query(ge=1, le=10000, description="页码大小"),
    start_time: str = Query("2023-01-01", description="开始时间", alias="startTime"),
    end_time: str = Query("2099-01-01", description="结束时间", alias="endTime"),
    collection: str | None = Query(None, description="知识库"),
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

    return PaginatedResponse.create(
        items=[MetricData.model_validate(metric) for metric in metrics], total=total, current=current, size=size
    )


@router.get("/hot-questions", response_model=BaseResponse[List[HotQuestionData]], summary="获取热点话题")
async def get_hot_questions(
    collection: str | None = Query(None, description="知识库"),
    days: int | None = Query(None, description="热点天数"),
    limit: int | None = Query(None, description="返回数据数"),
):
    return BaseResponse(data=question_analyzer.get_hot_questions(collection_name=collection, days=days, limit=limit))
