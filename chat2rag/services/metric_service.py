import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

from chat2rag.core.crud import CRUDBase
from chat2rag.models import Metric
from chat2rag.schemas.metric import MetricCreate, MetricUpdate


class MetricService(CRUDBase[Metric, MetricCreate, MetricUpdate]):
    def __init__(self):
        super().__init__(Metric)

    def get_metrics_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        model: Optional[str] = None,
        collection: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Metric], int]:
        """获取时间范围内的指标记录（分页）"""
        filters = [self.between_dates("create_time", start_time, end_time)]

        if model:
            filters.append(Metric.model == model)
        if collection:
            filters.append(Metric.collections.like(f"%{collection}%"))

        order_by = [self.order_by_field("create_time", descending=True)]

        return self.get_paginated(page=page, page_size=page_size, filters=filters, order_by=order_by)

    def get_performance_stats(
        self,
        start_time: datetime,
        end_time: datetime,
        model: Optional[str] = None,
        group_by_hour: bool = False,
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        获取指定时间范围内的性能统计数据

        Args:

            start_time: 开始时间
            end_time: 结束时间
            model: 可选的模型名称过滤
            group_by_hour: 是否按小时分组统计

        Returns:
            性能统计数据
        """
        filters = [self.between_dates("create_time", start_time, end_time)]

        if model:
            filters.append(Metric.model == model)

        if not group_by_hour:
            # 不分组，返回整体统计
            query = self.db.query(
                func.avg(Metric.total_ms).label("avg_response_time"),
                func.avg(Metric.first_response_ms).label("avg_first_response_time"),
                func.avg(Metric.document_ms).label("avg_document_retrieval_time"),
                func.avg(Metric.tool_ms).label("avg_tool_execution_time"),
                func.avg(Metric.input_tokens).label("avg_input_tokens"),
                func.avg(Metric.output_tokens).label("avg_output_tokens"),
                func.count(Metric.message_id).label("total_requests"),
                func.sum(Metric.input_tokens).label("total_input_tokens"),
                func.sum(Metric.output_tokens).label("total_output_tokens"),
                func.min(Metric.total_ms).label("min_response_time"),
                func.max(Metric.total_ms).label("max_response_time"),
            ).filter(*filters)

            result = query.first()

            # 转换为字典返回
            return {
                "avg_response_time": (float(result.avg_response_time) if result.avg_response_time else 0),
                "avg_first_response_time": (
                    float(result.avg_first_response_time) if result.avg_first_response_time else 0
                ),
                "avg_document_retrieval_time": (
                    float(result.avg_document_retrieval_time) if result.avg_document_retrieval_time else 0
                ),
                "avg_tool_execution_time": (
                    float(result.avg_tool_execution_time) if result.avg_tool_execution_time else 0
                ),
                "avg_input_tokens": (float(result.avg_input_tokens) if result.avg_input_tokens else 0),
                "avg_output_tokens": (float(result.avg_output_tokens) if result.avg_output_tokens else 0),
                "total_requests": result.total_requests,
                "total_input_tokens": result.total_input_tokens,
                "total_output_tokens": result.total_output_tokens,
                "min_response_time": (float(result.min_response_time) if result.min_response_time else 0),
                "max_response_time": (float(result.max_response_time) if result.max_response_time else 0),
            }
        else:
            # 按小时分组统计
            hour_extract_expr = func.date_trunc("hour", Metric.create_time).label("hour")

            query = (
                self.db.query(
                    hour_extract_expr,
                    func.avg(Metric.total_ms).label("avg_response_time"),
                    func.count(Metric.message_id).label("total_requests"),
                    func.sum(Metric.input_tokens).label("total_input_tokens"),
                    func.sum(Metric.output_tokens).label("total_output_tokens"),
                )
                .filter(*filters)
                .group_by(hour_extract_expr)
                .order_by(hour_extract_expr)
            )

            results = query.all()

            # 转换为字典列表
            return [
                {
                    "hour": result.hour.isoformat(),
                    "avg_response_time": (float(result.avg_response_time) if result.avg_response_time else 0),
                    "total_requests": result.total_requests,
                    "total_input_tokens": result.total_input_tokens,
                    "total_output_tokens": result.total_output_tokens,
                }
                for result in results
            ]

    def get_latest_metrics(self, limit: int = 10) -> List[Metric]:
        """
        获取最新的指标记录

        Args:
            db: 数据库会话
            limit: 返回的最大记录数

        Returns:
            最新的指标记录列表
        """
        return self.db.query(Metric).order_by(desc(Metric.create_time)).limit(limit).all()

    def update_metric(
        self,
        message_id: str,
        metric_data: Union[MetricUpdate, Dict[str, Any]],
    ) -> Optional[Metric]:
        """
        更新指标记录

        Args:
            db: 数据库会话
            message_id: 消息ID
            metric_data: 更新的指标数据

        Returns:
            更新后的指标记录或None
        """
        db_obj = self.get(message_id)
        if db_obj:
            return self.update(db_obj=db_obj, obj_in=metric_data)
        return None

    async def create_metric(self, metric_data: Union[MetricCreate, Dict[str, Any]]) -> Metric:
        """
        创建新的指标记录

        Args:
            metric_data: 指标数据

        Returns:
            创建的指标记录
        """
        # 如果没有提供message_id，自动生成一个
        if isinstance(metric_data, dict) and "message_id" not in metric_data:
            metric_data["message_id"] = str(uuid.uuid4())
        elif isinstance(metric_data, MetricCreate) and not metric_data.message_id:
            metric_data.message_id = str(uuid.uuid4())

        return await self.create(obj_in=metric_data)

    def get_model_usage_stats(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """
        获取不同模型的使用统计

        Args:
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            模型使用统计数据
        """
        filters = [self.between_dates("create_time", start_time, end_time)]

        query = (
            self.db.query(
                Metric.model,
                func.count(Metric.message_id).label("request_count"),
                func.avg(Metric.total_ms).label("avg_response_time"),
                func.sum(Metric.input_tokens).label("total_input_tokens"),
                func.sum(Metric.output_tokens).label("total_output_tokens"),
            )
            .filter(*filters)
            .group_by(Metric.model)
        )

        results = query.all()

        return [
            {
                "model": result.model,
                "request_count": result.request_count,
                "avg_response_time": (float(result.avg_response_time) if result.avg_response_time else 0),
                "total_input_tokens": result.total_input_tokens,
                "total_output_tokens": result.total_output_tokens,
            }
            for result in results
        ]

    def get_tool_usage_stats(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """
        获取工具使用统计

        Args:
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            工具使用统计数据
        """
        # 这里需要一些特殊处理，因为tools字段是逗号分隔的字符串
        # 使用SQL函数处理
        sql = """
        WITH tool_usage AS (
            SELECT 
                unnest(string_to_array(tools, ',')) AS tool_name,
                COUNT(*) AS usage_count,
                AVG(tool_ms) AS avg_execution_time
            FROM metrics
            WHERE create_time BETWEEN :start_time AND :end_time
                AND tools IS NOT NULL AND tools != ''
            GROUP BY tool_name
        )
        SELECT * FROM tool_usage ORDER BY usage_count DESC
        """

        result = self.db.execute(text(sql), {"start_time": start_time, "end_time": end_time})

        return [
            {
                "tool_name": row.tool_name,
                "usage_count": row.usage_count,
                "avg_execution_time": (float(row.avg_execution_time) if row.avg_execution_time else 0),
            }
            for row in result
        ]

    def get_collection_usage_stats(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """
        获取知识库使用统计

        Args:
            db: 数据库会话
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            知识库使用统计数据
        """
        # 与工具使用统计类似，需要处理逗号分隔的字符串
        sql = """
        WITH collection_usage AS (
            SELECT 
                unnest(string_to_array(collections, ',')) AS collection_name,
                COUNT(*) AS usage_count,
                AVG(document_ms) AS avg_retrieval_time,
                AVG(document_count) AS avg_document_count
            FROM metrics
            WHERE create_time BETWEEN :start_time AND :end_time
                AND collections IS NOT NULL AND collections != ''
            GROUP BY collection_name
        )
        SELECT * FROM collection_usage ORDER BY usage_count DESC
        """

        result = self.db.execute(text(sql), {"start_time": start_time, "end_time": end_time})

        return [
            {
                "collection_name": row.collection_name,
                "usage_count": row.usage_count,
                "avg_retrieval_time": (float(row.avg_retrieval_time) if row.avg_retrieval_time else 0),
                "avg_document_count": (float(row.avg_document_count) if row.avg_document_count else 0),
            }
            for row in result
        ]

    def get_error_stats(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """
        获取错误统计信息

        Args:
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            错误统计数据
        """
        filters = [self.between_dates("create_time", start_time, end_time)]

        # 总请求数
        total_count = self.db.query(func.count(Metric.message_id)).filter(*filters).scalar()

        # 错误请求数（有错误信息的请求）
        error_filters = filters.copy()
        error_filters.append(Metric.error_message.isnot(None))
        error_count = self.db.query(func.count(Metric.message_id)).filter(*error_filters).scalar()

        # 计算错误率
        error_rate = (error_count / total_count) if total_count > 0 else 0

        # 获取常见错误类型及数量
        common_errors_query = (
            self.db.query(Metric.error_message, func.count(Metric.message_id).label("count"))
            .filter(*error_filters)
            .group_by(Metric.error_message)
            .order_by(desc("count"))
            .limit(10)
        )

        common_errors = [{"error_message": row.error_message, "count": row.count} for row in common_errors_query]

        return {
            "total_requests": total_count,
            "error_count": error_count,
            "error_rate": error_rate,
            "common_errors": common_errors,
        }

    def get_time_series_data(
        self,
        start_time: datetime,
        end_time: datetime,
        interval: str = "hour",  # 'hour', 'day', 'week', 'month'
        metric: str = "count",  # 'count', 'avg_response_time', 'avg_tokens'
    ) -> List[Dict[str, Any]]:
        """
        获取时间序列数据，支持不同时间间隔和不同指标

        Args:

            start_time: 开始时间
            end_time: 结束时间
            interval: 时间间隔，支持hour、day、week、month
            metric: 统计指标，支持count、avg_response_time、avg_tokens

        Returns:
            时间序列数据
        """
        # 构建时间截断表达式
        if interval == "hour":
            time_expr = func.date_trunc("hour", Metric.create_time).label("time_bucket")
        elif interval == "day":
            time_expr = func.date_trunc("day", Metric.create_time).label("time_bucket")
        elif interval == "week":
            time_expr = func.date_trunc("week", Metric.create_time).label("time_bucket")
        elif interval == "month":
            time_expr = func.date_trunc("month", Metric.create_time).label("time_bucket")
        else:
            raise ValueError(f"不支持的时间间隔: {interval}")

        # 构建指标表达式
        if metric == "count":
            metric_expr = func.count(Metric.message_id).label("value")
        elif metric == "avg_response_time":
            metric_expr = func.avg(Metric.total_ms).label("value")
        elif metric == "avg_tokens":
            metric_expr = func.avg(Metric.input_tokens + Metric.output_tokens).label("value")
        else:
            raise ValueError(f"不支持的指标: {metric}")

        # 执行查询
        filters = [self.between_dates("create_time", start_time, end_time)]

        query = self.db.query(time_expr, metric_expr).filter(*filters).group_by(time_expr).order_by(time_expr)

        results = query.all()

        return [
            {
                "time": result.time_bucket.isoformat(),
                "value": float(result.value) if result.value is not None else 0,
            }
            for result in results
        ]

    def get_chat_completion_metrics(self, chat_id: str) -> Dict[str, Any]:
        """
        获取特定会话的完整指标统计

        Args:
            db: 数据库会话
            chat_id: 会话ID

        Returns:
            会话指标统计
        """
        filters = [Metric.chat_id == chat_id]

        # 获取会话基本信息
        first_message = self.db.query(Metric).filter(*filters).order_by(Metric.create_time).first()
        last_message = self.db.query(Metric).filter(*filters).order_by(desc(Metric.create_time)).first()

        if not first_message or not last_message:
            return {"error": "未找到会话记录"}

        # 计算会话持续时间（秒）
        duration_seconds = (last_message.create_time - first_message.create_time).total_seconds()

        # 获取会话轮次
        rounds = self.db.query(func.count(Metric.message_id)).filter(*filters).scalar()

        # 获取总token使用量
        token_query = self.db.query(
            func.sum(Metric.input_tokens).label("total_input_tokens"),
            func.sum(Metric.output_tokens).label("total_output_tokens"),
        ).filter(*filters)

        token_result = token_query.first()

        # 获取平均响应时间
        avg_response_time = self.db.query(func.avg(Metric.total_ms)).filter(*filters).scalar()

        # 获取工具使用情况
        tools_used = []
        tools_query = self.db.query(Metric.tools).filter(*filters).filter(Metric.tools.isnot(None))

        for row in tools_query:
            if row.tools:
                tools_list = row.tools.split(",")
                tools_used.extend(tools_list)

        # 计算工具使用频率
        tool_frequency = {}
        for tool in tools_used:
            tool = tool.strip()
            if tool:
                tool_frequency[tool] = tool_frequency.get(tool, 0) + 1

        return {
            "chat_id": chat_id,
            "start_time": first_message.create_time.isoformat(),
            "end_time": last_message.create_time.isoformat(),
            "duration_seconds": duration_seconds,
            "rounds": rounds,
            "total_input_tokens": (token_result.total_input_tokens if token_result.total_input_tokens else 0),
            "total_output_tokens": (token_result.total_output_tokens if token_result.total_output_tokens else 0),
            "avg_response_time_ms": (float(avg_response_time) if avg_response_time else 0),
            "tools_usage": [{"tool": k, "count": v} for k, v in tool_frequency.items()],
        }

    def export_metrics_to_dict(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: List[Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        将指标数据导出为字典列表，便于导出为CSV或JSON

        Args:

            start_time: 开始时间
            end_time: 结束时间
            filters: 额外的过滤条件

        Returns:
            字典列表形式的指标数据
        """
        base_filters = [self.between_dates("create_time", start_time, end_time)]

        if filters:
            base_filters.extend(filters)

        metrics = self.db.query(Metric).filter(*base_filters).order_by(Metric.create_time).all()

        result = []
        for metric in metrics:
            # 转换为字典，处理特殊字段
            metric_dict = {
                "message_id": metric.message_id,
                "create_time": metric.create_time.isoformat(),
                "chat_id": metric.chat_id,
                "chat_rounds": metric.chat_rounds,
                "question": metric.question,
                "answer": metric.answer,
                "model": metric.model,
                "prompt": metric.prompt,
                "tools": metric.tools,
                "collections": metric.collections,
                "document_count": metric.document_count,
                "document_ms": metric.document_ms,
                "tool_ms": metric.tool_ms,
                "first_response_ms": metric.first_response_ms,
                "total_ms": metric.total_ms,
                "input_tokens": metric.input_tokens,
                "output_tokens": metric.output_tokens,
                "error_message": metric.error_message,
                "precision_mode": metric.precision_mode,
            }

            # 处理JSON字段
            if metric.retrieval_params:
                metric_dict["retrieval_params"] = metric.retrieval_params

            if metric.tool_result:
                metric_dict["tool_result"] = metric.tool_result

            if metric.extra_params:
                metric_dict["extra_params"] = metric.extra_params

            if metric.meta_data:
                metric_dict["meta_data"] = metric.meta_data

            result.append(metric_dict)

        return result

    def get_dashboard_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        获取仪表盘概要数据

        Args:
            db: 数据库会话
            days: 最近天数

        Returns:
            仪表盘概要数据
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        # 获取总请求数
        total_requests = self.count(filters=[self.between_dates("create_time", start_time, end_time)])

        # 获取今日请求数
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_requests = self.count(filters=[self.between_dates("create_time", today_start, end_time)])

        # 获取平均响应时间
        avg_response_time = (
            self.db.query(func.avg(Metric.total_ms))
            .filter(self.between_dates("create_time", start_time, end_time))
            .scalar()
        )

        # 获取错误率
        error_count = self.count(
            filters=[
                self.between_dates("create_time", start_time, end_time),
                Metric.error_message.isnot(None),
            ],
        )
        error_rate = (error_count / total_requests) if total_requests > 0 else 0

        # 获取总token使用量
        token_query = self.db.query(
            func.sum(Metric.input_tokens).label("total_input_tokens"),
            func.sum(Metric.output_tokens).label("total_output_tokens"),
        ).filter(self.between_dates("create_time", start_time, end_time))

        token_result = token_query.first()

        # 获取模型使用分布
        model_usage = self.get_model_usage_stats(start_time, end_time)

        return {
            "period_days": days,
            "total_requests": total_requests,
            "today_requests": today_requests,
            "avg_response_time_ms": (float(avg_response_time) if avg_response_time else 0),
            "error_rate": error_rate,
            "total_input_tokens": (token_result.total_input_tokens if token_result.total_input_tokens else 0),
            "total_output_tokens": (token_result.total_output_tokens if token_result.total_output_tokens else 0),
            "model_distribution": model_usage,
        }


metric_service = MetricService()
