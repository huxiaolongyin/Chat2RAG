import math
from typing import List


def hit_at_k(retrieved_ids: List[str], relevant_ids: List[str], k: int) -> int:
    """
    Hit@K: 正确答案是否在 top-K 中
    返回 1 表示命中，0 表示未命中
    """
    if not relevant_ids:
        return 0
    return int(bool(set(retrieved_ids[:k]) & set(relevant_ids)))


def recall_at_k(retrieved_ids: List[str], relevant_ids: List[str], k: int) -> float:
    """
    Recall@K: 正确答案在 top-K 中的比例
    对于单相关文档场景，等同于 Hit@K
    """
    if not relevant_ids:
        return 0.0
    hits = len(set(retrieved_ids[:k]) & set(relevant_ids))
    return hits / len(relevant_ids)


def mrr(retrieved_ids: List[str], relevant_ids: List[str]) -> float:
    """
    MRR (Mean Reciprocal Rank): 正确答案排名的倒数
    如果正确答案排在第 r 位，则返回 1/r
    如果未找到，返回 0
    """
    if not relevant_ids:
        return 0.0
    for i, rid in enumerate(retrieved_ids):
        if rid in relevant_ids:
            return 1.0 / (i + 1)
    return 0.0


def dcg_at_k(retrieved_ids: List[str], relevant_ids: List[str], k: int) -> float:
    """
    DCG@K (Discounted Cumulative Gain)
    DCG = sum(rel_i / log2(i + 2)) for i in top-K
    其中 rel_i = 1 如果文档相关，否则 0
    """
    dcg = 0.0
    for i, rid in enumerate(retrieved_ids[:k]):
        if rid in relevant_ids:
            dcg += 1.0 / math.log2(i + 2)
    return dcg


def idcg_at_k(relevant_count: int, k: int) -> float:
    """
    IDCG@K (Ideal DCG): 理想情况下的 DCG
    假设所有相关文档都排在最前面
    """
    idcg = 0.0
    for i in range(min(relevant_count, k)):
        idcg += 1.0 / math.log2(i + 2)
    return idcg


def ndcg_at_k(retrieved_ids: List[str], relevant_ids: List[str], k: int) -> float:
    """
    NDCG@K (Normalized Discounted Cumulative Gain)
    NDCG = DCG / IDCG
    考虑排序位置的综合指标
    """
    if not relevant_ids:
        return 0.0

    dcg = dcg_at_k(retrieved_ids, relevant_ids, k)
    idcg = idcg_at_k(len(relevant_ids), k)

    if idcg == 0:
        return 0.0

    return dcg / idcg
