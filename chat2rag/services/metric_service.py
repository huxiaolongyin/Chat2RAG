from datetime import datetime
from typing import List

from tortoise.expressions import Q

from chat2rag.core.crud import CRUDBase
from chat2rag.models import Metric
from chat2rag.schemas.metric import (
    ChatSessionData,
    MetricCreate,
    MetricUpdate,
    SessionStatsData,
)


class MetricService(CRUDBase[Metric, MetricCreate, MetricUpdate]):
    def __init__(self):
        super().__init__(Metric)

    async def get_sessions_list(
        self,
        page: int = 1,
        page_size: int = 20,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        chat_id: str | None = None,
    ) -> tuple[int, List[ChatSessionData]]:
        from tortoise.functions import Count, Max, Min, Sum

        q = Q(chat_id__isnull=False)
        if start_time:
            q &= Q(create_time__gte=start_time)
        if end_time:
            q &= Q(create_time__lt=end_time)
        if chat_id:
            q &= Q(chat_id=chat_id)

        aggregated = await (
            Metric.filter(q)
            .group_by("chat_id")
            .annotate(
                message_count=Count("message_id"),
                total_input_tokens=Sum("input_tokens"),
                total_output_tokens=Sum("output_tokens"),
                min_create_time=Min("create_time"),
                max_update_time=Max("update_time"),
            )
            .values(
                "chat_id",
                "message_count",
                "total_input_tokens",
                "total_output_tokens",
                "min_create_time",
                "max_update_time",
            )
        )

        chat_ids = [row["chat_id"] for row in aggregated]
        first_messages = await (
            Metric.filter(chat_id__in=chat_ids)
            .order_by("chat_id", "create_time")
            .values("chat_id", "question", "model", "collections")
        )

        first_msg_map: dict[str, dict] = {}
        for msg in first_messages:
            cid = msg["chat_id"]
            if cid not in first_msg_map:
                first_msg_map[cid] = msg

        sessions = []
        for row in aggregated:
            cid = row["chat_id"]
            first_msg = first_msg_map.get(cid, {})
            sessions.append(
                {
                    "chat_id": cid,
                    "first_question": first_msg.get("question") or "",
                    "message_count": row["message_count"] or 0,
                    "total_input_tokens": row["total_input_tokens"] or 0,
                    "total_output_tokens": row["total_output_tokens"] or 0,
                    "model": first_msg.get("model"),
                    "collections": first_msg.get("collections"),
                    "create_time": row["min_create_time"],
                    "update_time": row["max_update_time"],
                }
            )

        sessions.sort(key=lambda x: x["update_time"], reverse=True)
        total = len(sessions)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated = sessions[start_idx:end_idx]

        return total, [ChatSessionData(**s) for s in paginated]

    async def get_session_stats(self, chat_id: str) -> SessionStatsData | None:
        metrics = await Metric.filter(chat_id=chat_id).values(
            "input_tokens",
            "output_tokens",
            "first_response_ms",
            "total_ms",
            "model",
            "collections",
        )

        if not metrics:
            return None

        total_input = sum(m["input_tokens"] or 0 for m in metrics)
        total_output = sum(m["output_tokens"] or 0 for m in metrics)
        first_response_list = [
            m["first_response_ms"] for m in metrics if m["first_response_ms"]
        ]
        total_ms_list = [m["total_ms"] for m in metrics if m["total_ms"]]
        models = list(set(m["model"] for m in metrics if m["model"]))
        collections_raw = [m["collections"] for m in metrics if m["collections"]]
        collections = list(
            set(c for cs in collections_raw for c in cs.split(",") if c.strip())
        )

        return SessionStatsData(
            chat_id=chat_id,
            message_count=len(metrics),
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_tokens=total_input + total_output,
            avg_first_response_ms=sum(first_response_list) / len(first_response_list)
            if first_response_list
            else None,
            avg_total_ms=sum(total_ms_list) / len(total_ms_list)
            if total_ms_list
            else None,
            models_used=models,
            collections_used=collections,
        )


metric_service = MetricService()
