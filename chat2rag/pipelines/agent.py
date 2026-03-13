from typing import Any, Callable, Dict, List

from haystack import AsyncPipeline
from haystack.components.agents import Agent
from haystack.components.builders import ChatPromptBuilder
from haystack.components.embedders import OpenAITextEmbedder
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.components.joiners import DocumentJoiner
from haystack.dataclasses import ChatMessage
from haystack.utils import Secret
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore
from qdrant_client.models import Filter

from chat2rag.config import CONFIG
from chat2rag.core.logger import get_logger
from chat2rag.pipelines.base import BasePipeline
from chat2rag.services.tool_service import mcp_service
from chat2rag.utils.merge_kwargs import recursive_tuple_to_dict
from chat2rag.utils.qdrant_store import detect_vector_mode, get_client

logger = get_logger(__name__)


DEFAULT_DOCUMENTS_PARSE = """
{% if documents %}
    {% for doc in documents %}
content: {{ doc.content }} score: {{ doc.score }}
    {% endfor %}
{% endif %}                                                 
"""


class AgentPipeline(BasePipeline[AsyncPipeline]):
    def __init__(
        self,
        collections: List[str],
        model: str,
        tools: List[str] = [],
        api_base_url: str = "",
        api_key: str = "",
        generation_kwargs: Dict[str, Any] = {},
        retrieval_mode: str | None = None,
    ):
        super().__init__()
        self._collections = collections if collections else []
        self._model = model
        self._tools = []
        self._tool_list = tools
        self._api_base_url = api_base_url
        self._api_key = api_key
        self._generation_kwargs = recursive_tuple_to_dict(generation_kwargs)
        self._retrieval_mode = retrieval_mode or CONFIG.RETRIEVAL_MODE
        self._vector_modes: Dict[str, str] = {}

    async def _prepare_async_resources(self):
        """异步加载工具并检测向量模式"""
        if self._tool_list:
            loaded_tools = await mcp_service.get_by_names(self._tool_list)
            if loaded_tools:
                self._tools.extend(loaded_tools)
            else:
                logger.warning(f"Failed to load tools: {self._tool_list}")

        client = get_client()
        for collection in self._collections:
            mode = await detect_vector_mode(client, collection)
            self._vector_modes[collection] = mode
            logger.info(f"Detected vector mode for '{collection}': {mode}")

    def _initialize_pipeline(self) -> AsyncPipeline:
        try:
            pipeline = AsyncPipeline()
            pipeline.add_component(
                "embedder",
                OpenAITextEmbedder(
                    api_base_url=CONFIG.EMBEDDING_OPENAI_URL,
                    api_key=Secret.from_token(CONFIG.EMBEDDING_API_KEY),
                    model=CONFIG.EMBEDDING_MODEL,
                    dimensions=CONFIG.EMBEDDING_DIMENSIONS,
                ),
            )
            for idx, collection in enumerate(self._collections):
                retriever_name = f"retriever_{idx}"
                vector_mode = self._vector_modes.get(collection, "hybrid")
                use_sparse = vector_mode == "hybrid"

                document_store = QdrantDocumentStore(
                    location=CONFIG.QDRANT_LOCATION,
                    embedding_dim=CONFIG.EMBEDDING_DIMENSIONS,
                    index=collection,
                    use_sparse_embeddings=use_sparse,
                )
                document_store._async_client = get_client()
                pipeline.add_component(
                    retriever_name,
                    QdrantEmbeddingRetriever(document_store=document_store),
                )
                pipeline.connect(
                    "embedder.embedding", f"{retriever_name}.query_embedding"
                )
            pipeline.add_component("doc_joiner", DocumentJoiner())

            for idx in range(len(self._collections)):
                pipeline.connect(f"retriever_{idx}.documents", "doc_joiner.documents")

            pipeline.add_component(
                "builder",
                instance=ChatPromptBuilder(
                    template=[ChatMessage.from_user(DEFAULT_DOCUMENTS_PARSE)],
                    required_variables=["documents"],
                ),
            )
            pipeline.add_component(
                "agent",
                Agent(
                    chat_generator=OpenAIChatGenerator(
                        api_key=Secret.from_token(self._api_key),
                        model=self._model,
                        api_base_url=self._api_base_url,
                        generation_kwargs=self._generation_kwargs,
                    ),
                    raise_on_tool_invocation_failure=False,
                    tools=self._tools,
                ),
            )
            pipeline.connect("doc_joiner.documents", "builder.documents")
            pipeline.connect("builder", "agent")

            return pipeline

        except Exception as e:
            logger.exception("Failed to initialize the Agent pipeline")
            raise

    async def run(
        self,
        query: str,
        top_k: int,
        score_threshold: float,
        messages: List[ChatMessage],
        filters: Dict[str, Any] | Filter | None = None,
        extra_params: Dict[str, Any] = {},
        streaming_callback: Callable | None = None,
    ):
        """
        Run the pipeline with the given parameters.
        """
        # 构建 retriever 参数
        retriever_params = {}
        for idx in range(len(self._collections)):
            retriever_params[f"retriever_{idx}"] = {
                "top_k": top_k,
                "score_threshold": score_threshold,
                "filters": filters,
            }

        return await self.pipeline.run_async(
            {
                "embedder": {"text": query},
                **retriever_params,  # 展开所有 retriever 的参数
                "builder": {
                    "template": messages,
                    "template_variables": {"query": query} | extra_params,
                },
                "agent": {
                    "streaming_callback": streaming_callback,
                },
            },
            # include_outputs_from=set("doc_joiner"),
        )
