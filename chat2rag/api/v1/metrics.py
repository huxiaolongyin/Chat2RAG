from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Query
from tortoise.expressions import Q

from chat2rag.schemas.base import BaseResponse, PaginatedResponse
from chat2rag.schemas.common import Current
from chat2rag.schemas.metric import (
    ChatSessionData,
    HotQuestionData,
    MetricData,
    SessionStatsData,
)
from chat2rag.services.metric_service import metric_service
from chat2rag.services.question_analyzer import QuestionAnalyzer

router = APIRouter()


@router.get("", response_model=PaginatedResponse[MetricData], summary="获取对话历史")
@router.get("/list", response_model=PaginatedResponse[MetricData], summary="获取对话历史")
async def get_metrics_list(
    current: Current = 1,
    size: int = Query(ge=1, le=10000, description="页码大小"),
    start_time: str = Query("2023-01-01", description="开始时间", alias="startTime"),
    end_time: str = Query("2099-01-01", description="结束时间", alias="endTime"),
    collection: str | None = Query(None, description="知识库"),
    chat_id: str | None = Query(None, description="聊天会话ID", alias="chatId"),
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

    if chat_id:
        q &= Q(chat_id=chat_id)

    total, metrics = await metric_service.get_list(page=current, page_size=size, search=q, order=["-create_time"])

    return PaginatedResponse.create(
        items=[MetricData.model_validate(metric) for metric in metrics],
        total=total,
        current=current,
        size=size,
    )


@router.get(
    "/hot-questions",
    response_model=BaseResponse[List[HotQuestionData]],
    summary="获取热点话题",
)
async def get_hot_questions(
    collection: str | None = Query(None, description="知识库"),
    days: int | None = Query(None, description="热点天数"),
    limit: int | None = Query(None, description="返回数据数"),
):
    question_analyzer = QuestionAnalyzer()
    return BaseResponse(
        data=await question_analyzer.get_hot_questions(collection_name=collection, days=days, limit=limit)
    )


@router.get(
    "/sessions",
    response_model=PaginatedResponse[ChatSessionData],
    summary="获取会话列表",
)
async def get_sessions_list(
    current: Current = 1,
    size: int = Query(ge=1, le=10000, default=20, description="页码大小"),
    start_time: str | None = Query(None, description="开始时间", alias="startTime"),
    end_time: str | None = Query(None, description="结束时间", alias="endTime"),
    chat_id: str | None = Query(None, description="聊天会话ID", alias="chatId"),
):
    start_datetime = None
    end_datetime = None
    if start_time:
        start_datetime = datetime.strptime(start_time, "%Y-%m-%d")
    if end_time:
        end_datetime = datetime.strptime(end_time, "%Y-%m-%d").replace(hour=23, minute=59, second=59)

    total, sessions = await metric_service.get_sessions_list(
        page=current,
        page_size=size,
        start_time=start_datetime,
        end_time=end_datetime,
        chat_id=chat_id,
    )

    return PaginatedResponse.create(
        items=sessions,
        total=total,
        current=current,
        size=size,
    )


@router.get(
    "/sessions/{chat_id}/stats",
    response_model=BaseResponse[SessionStatsData],
    summary="获取会话统计",
)
async def get_session_stats(chat_id: str):
    stats = await metric_service.get_session_stats(chat_id)
    if not stats:
        raise HTTPException(status_code=404, detail="会话不存在")
    return BaseResponse(data=stats)
