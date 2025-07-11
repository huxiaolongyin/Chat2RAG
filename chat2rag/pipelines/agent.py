from typing import Any, Callable, Dict, List, Optional

from haystack import Pipeline
from haystack.components.agents import Agent
from haystack.components.builders import ChatPromptBuilder
from haystack.components.embedders import OpenAITextEmbedder
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.components.joiners import DocumentJoiner
from haystack.dataclasses import ChatMessage
from haystack.utils import Secret
from haystack_integrations.components.retrievers.qdrant import QdrantEmbeddingRetriever
from haystack_integrations.document_stores.qdrant import QdrantDocumentStore

from chat2rag.config import CONFIG
from chat2rag.logger import get_logger
from chat2rag.pipelines.base import BasePipeline
from chat2rag.tools.tool_manager import tool_manager

logger = get_logger(__name__)


DEFAULT_DOCUMENTS_PARSE = """
{% if documents %}
    {% for doc in documents %}
content: {{ doc.content }} score: {{ doc.score }}
    {% endfor %}
{% endif %}                                                 
"""


class AgentPipeline(BasePipeline[Pipeline]):
    def __init__(self, collections: List[str], model: str, tools: List[str] = []):
        self._collections = collections[0]
        self._model = model
        if tools:
            self._tools = tool_manager.fetch_tools(tools)
        else:
            self._tools = tools
        super().__init__()

    def _initialize_pipeline(self) -> Pipeline:
        logger.debug("Initializing Agent search pipeline...")

        try:
            pipeline = Pipeline()
            pipeline.add_component(
                "embedder",
                OpenAITextEmbedder(
                    api_base_url=CONFIG.EMBEDDING_OPENAI_URL,
                    api_key=Secret.from_env_var("OPENAI_API_KEY"),
                    model=CONFIG.EMBEDDING_MODEL,
                    dimensions=CONFIG.EMBEDDING_DIMENSIONS,
                ),
            )
            pipeline.add_component(
                "retriever",
                QdrantEmbeddingRetriever(
                    document_store=QdrantDocumentStore(
                        host=CONFIG.QDRANT_HOST,
                        port=CONFIG.QDRANT_PORT,
                        embedding_dim=CONFIG.EMBEDDING_DIMENSIONS,
                        index=self._collections,
                    )
                ),
            )
            pipeline.add_component("doc_joiner", DocumentJoiner())
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
                        api_key=Secret.from_env_var("OPENAI_API_KEY"),
                        model=self._model,
                        api_base_url=CONFIG.OPENAI_BASE_URL,
                        generation_kwargs=CONFIG.GENERATION_KWARGS,
                    ),
                    raise_on_tool_invocation_failure=True,
                    tools=self._tools,
                ),
            )
            pipeline.connect("embedder.embedding", "retriever.query_embedding")
            pipeline.connect("retriever.documents", "doc_joiner.documents")
            pipeline.connect("doc_joiner.documents", "builder.documents")
            pipeline.connect("builder", "agent")

            return pipeline

        except Exception as e:
            logger.error(
                "Failed to initialize the Agent pipeline. Failure reason: %s", e
            )
            raise

    def run(
        self,
        query: str,
        top_k: int,
        score_threshold: float,
        doc_type: str,
        messages: List[ChatMessage],
        extra_params: Dict[str, Any] = {},
        streaming_callback: Optional[Callable] = None,
    ):
        """
        Run the pipeline with the given parameters.
        """
        return self.pipeline.run(
            {
                "embedder": {"text": query},
                "retriever": {
                    "top_k": top_k,
                    "score_threshold": score_threshold,
                    "filters": {
                        "field": "meta.type",
                        "operator": "==",
                        "value": doc_type,
                    },
                },
                "builder": {
                    "template": messages,
                    "template_variables": {"query": query} | extra_params,
                },
                "agent": {"streaming_callback": streaming_callback},
            },
            # include_outputs_from=["doc_joiner"],
        )
