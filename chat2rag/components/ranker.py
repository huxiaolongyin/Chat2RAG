from dataclasses import replace
from typing import Any

import httpx
from haystack import component, default_from_dict, default_to_dict
from haystack.dataclasses import Document
from haystack.utils import Secret

from chat2rag.core.logger import get_logger

logger = get_logger(__name__)


@component
class OpenRanker:
    _client: httpx.AsyncClient | None = None

    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        if cls._client is None:
            cls._client = httpx.AsyncClient(timeout=60.0)
        return cls._client

    @classmethod
    async def close(cls):
        if cls._client is not None:
            await cls._client.aclose()
            cls._client = None

    def __init__(
        self,
        model: str = "Qwen/Qwen3-Reranker-8B",
        top_k: int = 5,
        score_threshold: float = 0.0,
        api_key: Secret | None = None,
        api_base_url: str = "https://api.siliconflow.cn/v1/rerank",
    ):
        self.model = model
        self.top_k = top_k
        self.score_threshold = score_threshold
        self.api_key = api_key or Secret.from_env_var("RERANK_API_KEY")
        self.api_base_url = api_base_url

    def to_dict(self) -> dict[str, Any]:
        return default_to_dict(
            self,
            model=self.model,
            top_k=self.top_k,
            score_threshold=self.score_threshold,
            api_key=self.api_key.to_dict() if self.api_key else None,
            api_base_url=self.api_base_url,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OpenRanker":
        from haystack.utils import deserialize_secrets_inplace

        deserialize_secrets_inplace(data["init_parameters"], keys=["api_key"])
        return default_from_dict(cls, data)

    @component.output_types(documents=list[Document])
    def run(
        self,
        query: str,
        documents: list[Document],
        top_k: int | None = None,
        score_threshold: float | None = None,
    ) -> dict[str, list[Document]]:
        top_k = top_k or self.top_k
        score_threshold = score_threshold if score_threshold is not None else self.score_threshold
        if top_k <= 0:
            raise ValueError(f"top_k must be > 0, but got {top_k}")

        if not documents:
            return {"documents": []}

        doc_texts = [doc.content or "" for doc in documents]

        response = httpx.post(
            f"{self.api_base_url}",
            headers={
                "Authorization": f"Bearer {self.api_key.resolve_value()}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "query": query,
                "documents": doc_texts,
                "top_n": min(top_k, len(documents)),
            },
            timeout=60.0,
        )
        response.raise_for_status()

        results = response.json()["results"]
        sorted_docs = []
        for item in results:
            idx = item["index"]
            score = item["relevance_score"]
            if score >= score_threshold:
                sorted_docs.append(replace(documents[idx], score=score))

        logger.debug(
            f"Reranked {len(documents)} documents, returned {len(sorted_docs)} after score_threshold={score_threshold}"
        )
        return {"documents": sorted_docs}

    @component.output_types(documents=list[Document])
    async def run_async(
        self,
        query: str,
        documents: list[Document],
        top_k: int | None = None,
        score_threshold: float | None = None,
    ) -> dict[str, list[Document]]:
        top_k = top_k or self.top_k
        score_threshold = score_threshold if score_threshold is not None else self.score_threshold
        if top_k <= 0:
            raise ValueError(f"top_k must be > 0, but got {top_k}")

        if not documents:
            return {"documents": []}

        doc_texts = [doc.content or "" for doc in documents]

        client = await self.get_client()
        response = await client.post(
            self.api_base_url,
            headers={
                "Authorization": f"Bearer {self.api_key.resolve_value()}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "query": query,
                "documents": doc_texts,
                "top_n": min(top_k, len(documents)),
            },
        )
        response.raise_for_status()

        results = response.json()["results"]
        sorted_docs = []
        for item in results:
            idx = item["index"]
            score = item["relevance_score"]
            if score >= score_threshold:
                sorted_docs.append(replace(documents[idx], score=score))

        logger.debug(
            f"Reranked {len(documents)} documents, returned {len(sorted_docs)} after score_threshold={score_threshold}"
        )
        return {"documents": sorted_docs}
