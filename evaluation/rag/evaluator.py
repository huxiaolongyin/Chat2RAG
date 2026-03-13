import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from chat2rag.config import CONFIG
from chat2rag.pipelines.document import DocumentSearchPipeline
from chat2rag.utils.pipeline_cache import create_pipeline

from .metrics import hit_at_k, mrr, ndcg_at_k, recall_at_k


@dataclass
class EvalSample:
    query_id: str
    question: str
    relevant_doc_ids: List[str]


@dataclass
class EvalResult:
    query_id: str
    question: str
    retrieved_ids: List[str]
    scores: List[float]
    relevant_doc_ids: List[str]
    hit_k: dict = field(default_factory=dict)
    recall_k: dict = field(default_factory=dict)
    mrr_score: float = 0.0
    ndcg_k: dict = field(default_factory=dict)


@dataclass
class AggregatedResults:
    total_samples: int = 0
    hit_k: dict = field(default_factory=dict)
    recall_k: dict = field(default_factory=dict)
    mrr: float = 0.0
    ndcg_k: dict = field(default_factory=dict)
    detailed_results: List[EvalResult] = field(default_factory=list)


class RetrievalEvaluator:
    def __init__(
        self,
        collection_name: str = "eval",
        top_k_values: List[int] = None,
        score_threshold: float = 0.0,
    ):
        self.collection_name = collection_name
        self.top_k_values = top_k_values or [1, 3, 5, 10]
        self.max_k = max(self.top_k_values)
        self.score_threshold = score_threshold
        self.pipeline = None

    async def _init_pipeline(self):
        if self.pipeline is None:
            self.pipeline = await create_pipeline(
                DocumentSearchPipeline, qdrant_index=self.collection_name
            )

    def load_dataset(self, dataset_path: str) -> List[EvalSample]:
        path = Path(dataset_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset not found: {dataset_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        samples = []
        for item in data.get("samples", []):
            samples.append(
                EvalSample(
                    query_id=item.get("metadata", {}).get("query_id", ""),
                    question=item["question"],
                    relevant_doc_ids=item.get("relevant_doc_ids", []),
                )
            )
        return samples

    async def _retrieve(self, query: str) -> tuple[List[str], List[float]]:
        await self._init_pipeline()

        result = await self.pipeline.run(
            query=query,
            top_k=self.max_k,
            score_threshold=self.score_threshold,
        )

        documents = result.get("retriever", {}).get("documents", [])
        retrieved_ids = [doc.id for doc in documents]
        scores = [doc.score if doc.score is not None else 0.0 for doc in documents]

        return retrieved_ids, scores

    async def evaluate_sample(self, sample: EvalSample) -> EvalResult:
        retrieved_ids, scores = await self._retrieve(sample.question)

        result = EvalResult(
            query_id=sample.query_id,
            question=sample.question,
            retrieved_ids=retrieved_ids,
            scores=scores,
            relevant_doc_ids=sample.relevant_doc_ids,
        )

        for k in self.top_k_values:
            result.hit_k[k] = hit_at_k(retrieved_ids, sample.relevant_doc_ids, k)
            result.recall_k[k] = recall_at_k(retrieved_ids, sample.relevant_doc_ids, k)
            result.ndcg_k[k] = ndcg_at_k(retrieved_ids, sample.relevant_doc_ids, k)

        result.mrr_score = mrr(retrieved_ids, sample.relevant_doc_ids)

        return result

    async def evaluate(self, dataset_path: str) -> AggregatedResults:
        samples = self.load_dataset(dataset_path)
        total = len(samples)

        print(f"Starting evaluation on {total} samples...")
        print(f"Collection: {self.collection_name}")
        print(f"K values: {self.top_k_values}")
        print("-" * 50)

        start_time = time.time()
        detailed_results = []

        for i, sample in enumerate(samples):
            result = await self.evaluate_sample(sample)
            detailed_results.append(result)

            if (i + 1) % 100 == 0:
                elapsed = time.time() - start_time
                print(f"Progress: {i + 1}/{total} ({elapsed:.1f}s)")

        aggregated = self._aggregate_results(detailed_results)
        elapsed = time.time() - start_time
        print(f"\nEvaluation completed in {elapsed:.2f}s")

        return aggregated

    def _aggregate_results(self, results: List[EvalResult]) -> AggregatedResults:
        total = len(results)

        hit_k_sums = {k: 0 for k in self.top_k_values}
        recall_k_sums = {k: 0.0 for k in self.top_k_values}
        ndcg_k_sums = {k: 0.0 for k in self.top_k_values}
        mrr_sum = 0.0

        for r in results:
            for k in self.top_k_values:
                hit_k_sums[k] += r.hit_k[k]
                recall_k_sums[k] += r.recall_k[k]
                ndcg_k_sums[k] += r.ndcg_k[k]
            mrr_sum += r.mrr_score

        return AggregatedResults(
            total_samples=total,
            hit_k={k: v / total for k, v in hit_k_sums.items()},
            recall_k={k: v / total for k, v in recall_k_sums.items()},
            mrr=mrr_sum / total,
            ndcg_k={k: v / total for k, v in ndcg_k_sums.items()},
            detailed_results=results,
        )

    def generate_report(self, results: AggregatedResults) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append("           RETRIEVAL EVALUATION REPORT")
        lines.append("=" * 60)
        lines.append(f"Collection:    {self.collection_name}")
        lines.append(f"Total Samples: {results.total_samples}")
        lines.append(f"K Values:      {self.top_k_values}")
        lines.append("-" * 60)

        lines.append("\n--- Hit@K (命中率) ---")
        for k in self.top_k_values:
            val = results.hit_k[k]
            count = int(val * results.total_samples)
            lines.append(f"  Hit@{k:<2}: {val:.4f} ({count}/{results.total_samples})")

        lines.append("\n--- Recall@K (召回率) ---")
        for k in self.top_k_values:
            lines.append(f"  Recall@{k:<2}: {results.recall_k[k]:.4f}")

        lines.append("\n--- MRR (平均倒数排名) ---")
        lines.append(f"  MRR: {results.mrr:.4f}")

        lines.append("\n--- NDCG@K (归一化折损累计增益) ---")
        for k in self.top_k_values:
            lines.append(f"  NDCG@{k:<2}: {results.ndcg_k[k]:.4f}")

        lines.append("\n" + "=" * 60)

        return "\n".join(lines)

    def save_results(self, results: AggregatedResults, output_path: str):
        output = {
            "summary": {
                "collection": self.collection_name,
                "total_samples": results.total_samples,
                "k_values": self.top_k_values,
                "hit_k": results.hit_k,
                "recall_k": results.recall_k,
                "mrr": results.mrr,
                "ndcg_k": results.ndcg_k,
            },
            "detailed_results": [
                {
                    "query_id": r.query_id,
                    "question": r.question,
                    "retrieved_ids": r.retrieved_ids,
                    "scores": r.scores,
                    "relevant_doc_ids": r.relevant_doc_ids,
                    "hit_k": r.hit_k,
                    "recall_k": r.recall_k,
                    "mrr": r.mrr_score,
                    "ndcg_k": r.ndcg_k,
                }
                for r in results.detailed_results
            ],
        }

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"Results saved to: {output_path}")
