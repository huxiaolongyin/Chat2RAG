import asyncio
import time
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional

from haystack import Document, Pipeline
from haystack.components.builders import ChatPromptBuilder
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.components.generators.utils import print_streaming_chunk
from haystack.components.joiners.document_joiner import DocumentJoiner
from haystack.dataclasses import ChatMessage
from haystack.utils import Secret

from chat2rag.config import CONFIG
from chat2rag.logger import get_logger
from chat2rag.pipelines.base import BasePipeline
from chat2rag.pipelines.document import DocumentSearchPipeline
from chat2rag.pipelines.funciton import FunctionPipeline
from chat2rag.tools.tool_manager import tool_manager

logger = get_logger(__name__)


class RAGPipeline(BasePipeline):
    """
    RAG Pipeline combines the document retrieval pipeline and the function pipeline for large model response
    """

    @staticmethod
    @lru_cache(maxsize=32)
    def _create_doc_pipeline(index: str) -> DocumentSearchPipeline:
        """
        Create a new Document Search pipeline and cache it.
        """
        logger.info(f"Create a new Document Search pipeline: {index}")
        return DocumentSearchPipeline(index)

    @staticmethod
    def _create_function_pipeline(model: str, tools: List[str]) -> FunctionPipeline:
        """
        Create a new Function pipeline (and cache it).
        # TODO: Add mcp connection management
        """
        logger.info(f"Create a new Function pipeline: {model}")

        return FunctionPipeline(tools=tool_manager.fetch_tools(tools), model=model)

    def __init__(
        self,
        qdrant_index: Optional[List[str]] = None,
        model: str = CONFIG.DEFAULT_MODEL,
        stream_callback: Callable = print_streaming_chunk,
    ):
        """
        Initialize the RAG pipeline.

        Args:
            qdrant_index: The index name used for document retrieval
            model: The model used for generating responses
            stream_callback: The callback function used for streaming responses
        """

        # Create document retrieval pipelines
        if qdrant_index is not None:
            self.doc_pipelines = [
                self._create_doc_pipeline(index) for index in qdrant_index
            ]
        self.qdrant_index = qdrant_index
        self.model = model
        self._stream_callback = stream_callback

        super().__init__()

    def _initialize_pipeline(self) -> Pipeline:
        """
        Initialize the RAG pipeline.
        """
        logger.debug("Initializing RAG pipeline...")
        try:
            pipeline = Pipeline()
            prompt_builder = ChatPromptBuilder(
                variables=["query", "documents", "func_response"]
            )

            generator = OpenAIChatGenerator(
                model=self.model,
                api_key=Secret.from_env_var("OPENAI_API_KEY"),
                api_base_url=CONFIG.OPENAI_BASE_URL,
                streaming_callback=self._stream_callback,
            )
            pipeline.add_component("doc_joiner", DocumentJoiner())
            pipeline.add_component("prompt_builder", prompt_builder)
            pipeline.add_component("generator", generator)
            pipeline.connect("doc_joiner.documents", "prompt_builder.documents")
            pipeline.connect("prompt_builder.prompt", "generator")

            logger.debug("RAG pipeline initialized successfully.")
            return pipeline

        except Exception as e:
            logger.error("Failed to initialize RAG pipeline: %s", e, exc_info=True)
            raise

    async def _process_documents(
        self, documents_list: List[Document], stream_handler: Optional[Any] = None
    ) -> None:
        """
        Process the document retrieval results, and update the stream handler if needed.

        Args:
            documents_list: The list of retrieved documents
            stream_handler: An optional stream handler for progress updates
        """
        if stream_handler and hasattr(stream_handler, "set_doc_info"):
            stream_handler.set_doc_info(len(documents_list))
            # stream_handler.start()

    async def run(
        self,
        query: str,
        tools: List[str] = [],
        prefix_prompt: str = "",
        prompt_template: str = "",
        messages: List[ChatMessage] = [],
        top_k: int = None,
        score_threshold: float = None,
        generation_kwargs: Dict[str, Any] = {},
    ) -> dict:
        """
        Run the RAG pipeline with the given query and tools.

        Args:
            query: The question or order by the user
            tools: The list of tool names or ["all"]
            prefix_prompt: The prefix prompt for the prompt template
            prompt_template: A template used for generating responses
            messages: The chat messages for context
            top_k: The maximum number of documents to retrieve
            score_threshold: The minimum similarity score for document retrieval
            generation_kwargs: The additional parameters for the generator

        Returns:
            dict: Pipeline results, including the generated responses
        """
        start_time = time.time()
        logger.info(f"Start the RAG pipeline: <{query}>...")

        if not prompt_template:
            prompt_template = CONFIG.RAG_PROMPT_TEMPLATE
            logger.debug("Use the default rag prompt template.")
        if not top_k:
            top_k = CONFIG.TOP_K
            logger.debug("Use the default top_k.")
        if not score_threshold:
            score_threshold = CONFIG.SCORE_THRESHOLD
            logger.debug("Use the default score_threshold.")

        # Concurrently perform document retrieval and function calls
        tasks = []
        has_doc_tasks = False
        has_func_tasks = False
        if self.qdrant_index is not None:
            has_doc_tasks = True
            for pipeline in self.doc_pipelines:
                tasks.append(pipeline.run(query, top_k, score_threshold))
            logger.debug(f"Added {len(self.doc_pipelines)} document retrieval tasks")

        if tools:
            has_func_tasks = True
            try:
                func_pipeline = self._create_function_pipeline(self.model, tools)
                tasks.append(func_pipeline.run(query, prefix_prompt, messages))
                logger.debug(f"Added function pipeline task with tools: {tools}")
            except Exception as e:
                logger.error(f"Failed to create function pipeline: {e}")

        all_results = []
        if tasks:  # gather is executed only when there is a task
            try:
                all_results = await asyncio.gather(*tasks, return_exceptions=True)
                # Handle possible exceptions
                for i, result in enumerate(all_results):
                    if isinstance(result, Exception):
                        logger.error(f"Task {i} failed with error: {result}")
                        all_results[i] = (
                            {}
                        )  # Replace the exception with an empty result

            except Exception as e:
                logger.error(f"Failed to execute tasks: {e}")

        doc_results = []
        func_results = {}
        if has_doc_tasks and has_func_tasks:
            # Both document retrieval and function calls are available
            doc_results = all_results[:-1]
            func_results = (
                all_results[-1] if not isinstance(all_results[-1], Exception) else {}
            )
        elif has_doc_tasks:
            # Only document retrieval
            doc_results = all_results
        elif has_func_tasks:
            # Only function calls
            func_results = (
                all_results[0]
                if all_results and not isinstance(all_results[0], Exception)
                else {}
            )

        # Merge all documents
        documents_list = []
        for result in doc_results:
            if result and "retriever" in result and "documents" in result["retriever"]:
                documents_list.extend(result["retriever"]["documents"])

        # Get the stream handler
        stream_handler = (
            self._stream_callback.__self__
            if hasattr(self._stream_callback, "__self__")
            else None
        )
        await self._process_documents(documents_list, stream_handler)

        # Process the results of function calls
        func_response = ""
        if func_results and "tool_invoker" in func_results:
            for func_message in func_results["tool_invoker"]["tool_messages"]:
                if func_message.tool_call_result:
                    func_response += func_message.tool_call_result.result

        # Build the question template by Jinja2
        question_template = """
        问题：{{query}}；
        工具调用响应内容：{{func_response}}；
        文档参考内容(移除所有URL和网页地址再输出)：
        {% if documents %}
            {% for doc in documents %}
                content: {{ doc.content }} score: {{ doc.score }}
            {% endfor %}
        {% else %}
            None
        {% endif %}
        """

        prompt = [
            ChatMessage.from_system(prefix_prompt + prompt_template),
            *messages,
            ChatMessage.from_user(question_template),
        ]

        # Run the generation pipeline and return the result
        result = self.pipeline.run(
            data={
                "doc_joiner": {"documents": documents_list},
                "prompt_builder": {
                    "template": prompt,
                    "func_response": func_response,
                    "query": query,
                },
                "generator": {"generation_kwargs": generation_kwargs},
            },
            include_outputs_from=["doc_joiner"],
        )
        answer = result["generator"]["replies"][0].text
        logger.info(
            f"RAG pipeline completed. Query: <{query}>; Answer: <{answer}>, Total time: {time.time() - start_time:.2f}s"
        )

        return result
