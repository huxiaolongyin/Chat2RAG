import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from haystack.dataclasses import Document
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    VectorParams,
)
from sklearn.cluster import DBSCAN
from tortoise.expressions import Q

from chat2rag.config import CONFIG
from chat2rag.core.logger import get_logger
from chat2rag.models.metric import Metric
from chat2rag.pipelines.document import DocumentSearchPipeline, DocumentWriterPipeline
from chat2rag.utils.pipeline_cache import create_pipeline

logger = get_logger(__name__)


class QuestionAnalyzer:
    def __init__(self):
        self.collection_name = "questions"
        self.client = QdrantClient(location=CONFIG.QDRANT_LOCATION)
        if not self.client.collection_exists(self.collection_name):
            logger.warning(f"知识库 `{self.collection_name}` 不存在，进行新建")
            self.client.create_collection(
                self.collection_name,
                vectors_config=VectorParams(size=CONFIG.EMBEDDING_DIMENSIONS, distance=Distance.COSINE),
            )

        self.checkpoint_file = Path("data/checkpoint/metric_sync_checkpoint.json")

    @staticmethod
    def clean_text(text: str, level: str = "standard") -> str:
        """
        清洗文本

        Args:
            text: 原始文本
            level: 清洗级别
                - "basic": 基础清洗（空格、换行）
                - "standard": 标准清洗（推荐，包含标点、特殊字符）
                - "aggressive": 激进清洗（去除语气词、emoji等）

        Returns:
            清洗后的文本
        """
        if not text:
            return ""

        cleaned = text

        # === 基础清洗 ===
        # 去除首尾空格
        cleaned = cleaned.strip()

        # 统一换行符为空格
        cleaned = re.sub(r"[\r\n]+", " ", cleaned)

        # 去除多余空格
        cleaned = re.sub(r"\s+", " ", cleaned)

        if level == "basic":
            return cleaned

        # === 标准清洗 ===
        # 去除HTML标签
        cleaned = re.sub(r"<[^>]+>", "", cleaned)

        # 去除URL链接
        cleaned = re.sub(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+", "", cleaned
        )

        # 全角转半角
        cleaned = cleaned.replace("？", "?").replace("！", "!").replace("，", ",").replace("。", ".")
        cleaned = cleaned.replace("（", "(").replace("）", ")").replace("【", "[").replace("】", "]")

        # 统一多个问号/感叹号为单个
        cleaned = re.sub(r"[?？]+", "?", cleaned)
        cleaned = re.sub(r"[!！]+", "!", cleaned)

        # 去除特殊控制字符
        cleaned = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", cleaned)

        if level == "standard":
            return cleaned.strip()

        # === 激进清洗 ===
        # 去除emoji表情
        emoji_pattern = re.compile(
            "["
            "\U0001f600-\U0001f64f"  # 表情符号
            "\U0001f300-\U0001f5ff"  # 符号和象形文字
            "\U0001f680-\U0001f6ff"  # 交通和地图符号
            "\U0001f1e0-\U0001f1ff"  # 旗帜
            "\U00002702-\U000027b0"
            "\U000024c2-\U0001f251"
            "]+",
            flags=re.UNICODE,
        )
        cleaned = emoji_pattern.sub("", cleaned)

        # 去除常见语气词（可根据需要调整）
        filler_words = ["啊", "呢", "吧", "哦", "哈", "嗯", "唉", "哎", "呀"]
        for word in filler_words:
            cleaned = cleaned.replace(word, "")

        # 去除重复标点
        cleaned = re.sub(r"([,，.。;；:：])\1+", r"\1", cleaned)

        # 最终清理多余空格
        cleaned = re.sub(r"\s+", " ", cleaned)

        return cleaned.strip()

    async def add_or_update_question(
        self,
        collection_name: str,
        question_text: str,
        create_time: str = datetime.now().isoformat(),
        update_time: str = datetime.now().isoformat(),
    ):
        """添加新问题或更新已存在的相似问题"""
        try:
            # 清洗问题文本
            question_text = self.clean_text(question_text, level="standard")

            if not question_text:  # 清洗后为空则跳过
                return

            # 检查是否存在相似问题
            doc_search_pipeline = await create_pipeline(DocumentSearchPipeline, qdrant_index=self.collection_name)
            response = await doc_search_pipeline.run(
                question_text,
                top_k=1,
                score_threshold=0.95,
                filters={"field": "meta.collection_name", "operator": "==", "value": collection_name},
            )
            documents = response.get("retriever", {}).get("documents", "")
            if documents:
                question_id = documents[0].id
                question_meta = documents[0].meta

                # 更新计数和时间戳
                new_count = question_meta.get("count", 0) + 1
                updated_payload = {"meta": {**question_meta, "count": new_count, "update_time": update_time}}

                # 更新到数据库
                self.client.set_payload(
                    collection_name=self.collection_name,
                    payload=updated_payload,
                    points=Filter(must=[FieldCondition(key="id", match=MatchValue(value=question_id))]),
                )

            else:
                # 添加新问题到数据库
                doc_writer_pipeline = await create_pipeline(DocumentWriterPipeline, qdrant_index=self.collection_name)
                meta = {
                    "collection_name": collection_name,
                    "create_time": create_time,
                    "update_time": update_time,
                    "count": 1,
                }
                await doc_writer_pipeline.run([Document(content=question_text, meta=meta)])

        except Exception as e:
            logger.error("添加新问题或更新已存在的相似问题失败")

    def get_hot_questions(self, collection_name: str | None = None, days: int | None = None, limit: int | None = None):
        """
        获取热门问题

        Args:
            limit: 返回问题数量限制
            days: 时间范围（天数）

        Returns:
            热门问题列表
        """
        try:

            # 动态构建过滤条件
            filter_conditions = []

            if days is not None:
                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                filter_conditions.append(FieldCondition(key="meta.update_time", range={"gte": cutoff_date}))

            if collection_name:
                filter_conditions.append(FieldCondition(key="meta.collection_name", match={"value": collection_name}))

            # 如果有过滤条件则创建 Filter，否则为 None
            scroll_filter = Filter(must=filter_conditions) if filter_conditions else None

            # 搜索并按count排序
            search_result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=scroll_filter,
                limit=10000,
                with_payload=True,
                with_vectors=True,
            )

            points = search_result[0]
            if not points:
                return []

            # 准备聚类数据
            vectors = []
            questions_data = []

            for point in points:

                vectors.append(point.vector)
                meta = point.payload.get("meta", {})
                questions_data.append(
                    {
                        "id": point.id,
                        "text": point.payload.get("content", ""),
                        "count": meta.get("count", 0),
                        "collection": meta.get("collection_name", ""),
                        "create_time": meta.get("create_time", ""),
                        "update_time": meta.get("update_time", ""),
                        "point": point,
                    }
                )

            # 使用DBSCAN聚类
            clustering = DBSCAN(eps=0.15, min_samples=1, metric="cosine")
            cluster_labels = clustering.fit_predict(vectors)

            # 按簇分组问题
            clusters = {}
            noise_questions = []  # 噪声点（未被聚类的问题）

            for i, label in enumerate(cluster_labels):
                if label == -1:  # 噪声点
                    noise_questions.append(questions_data[i])
                else:
                    if label not in clusters:
                        clusters[label] = []
                    clusters[label].append(questions_data[i])

            # 处理每个簇，找出代表性问题并计算总count
            cluster_representatives = []

            for cluster_id, cluster_questions in clusters.items():
                # 找出簇内count最高的问题作为代表
                representative = max(cluster_questions, key=lambda x: x["count"])

                # 计算簇内所有问题的count总和
                total_count = sum(q["count"] for q in cluster_questions)

                clusters = [
                    {
                        "id": point["id"],
                        "text": point["text"],
                        "collection": point["collection"],
                        "create_time": point["create_time"],
                        "update_time": point["update_time"],
                        "count": point["count"],
                    }
                    for point in cluster_questions
                ]

                # 创建代表性问题记录
                cluster_representative = {
                    "id": representative["id"],
                    "representative_question": representative["text"],
                    "count": total_count,  # 使用簇的总count
                    "cluster_size": len(cluster_questions),  # 簇的大小
                    "create_time": representative["create_time"],
                    "update_time": representative["update_time"],
                    "similar_questions": clusters,
                }

                cluster_representatives.append(cluster_representative)

            # 处理噪声点（单独的问题）
            for noise_question in noise_questions:
                noise_representative = {
                    "id": noise_question["id"],
                    "representative_question": noise_question["text"],
                    "count": 1,  # 使用簇的总count
                    "cluster_size": 1,  # 簇的大小
                    "create_time": noise_question["create_time"],
                    "update_time": noise_question["update_time"],
                    "similar_questions": [],
                }

                cluster_representatives.append(noise_representative)

            # 按总count排序并返回前N个
            hot_questions = sorted(cluster_representatives, key=lambda x: x["count"], reverse=True)[:limit]

            return hot_questions

        except Exception as e:
            logger.error(f"获取热门问题时出错: {e}")
            return []

    def _load_checkpoint(self) -> str | None:
        """加载上次同步的时间记录点"""
        if not self.checkpoint_file.exists():
            return None

        try:
            with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("last_sync_time")

        except Exception as e:
            logger.error(f"加载checkpoint失败: {e}")
            return None

    def _save_checkpoint(self, sync_time: datetime | None = None):
        """保存同步时间记录点"""
        try:
            timestamp = sync_time or datetime.now()
            data = {"last_sync_time": timestamp.isoformat()}
            with open(self.checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"✓ Checkpoint已保存: {timestamp.isoformat()}")

        except Exception as e:
            logger.error(f"保存checkpoint失败: {e}")

    async def sync_from_metrics(self):
        """从Metric模型同步数据"""
        try:
            last_sync_time_str = self._load_checkpoint()

            if last_sync_time_str:
                # 将ISO格式字符串转换为datetime对象
                last_sync_time = datetime.fromisoformat(last_sync_time_str)
                # 修正查询操作符：glt -> gt (greater than)
                metrics = await Metric.filter(Q(create_time__gt=last_sync_time)).all().order_by("create_time")
                logger.info(f"增量同步: 从 {last_sync_time_str} 开始")
            else:
                metrics = await Metric.all().order_by("create_time")
                logger.info("全量同步: 首次同步所有数据")

            # 同步数据
            for metric in metrics:
                await self.add_or_update_question(
                    metric.collections, metric.question, metric.create_time.isoformat(), metric.update_time.isoformat()
                )

            # 同步成功后保存checkpoint
            self._save_checkpoint()
            logger.info(f"✓ 同步完成，共处理 {len(metrics)} 条记录")

            return True

        except Exception as e:
            logger.error(f"同步失败: {e}")
            return False


question_analyzer = QuestionAnalyzer()

if __name__ == "__main__":
    import asyncio

    import pandas as pd

    # question_df = pd.read_csv("temp/场景-问题.csv")
    # for collection_name, question in question_df.values:
    #     asyncio.run(qa.add_or_update_question(collection_name, question))
    print(json.dumps(question_analyzer.get_hot_questions(limit=20), ensure_ascii=False))
