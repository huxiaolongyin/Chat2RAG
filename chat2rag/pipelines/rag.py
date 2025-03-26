import asyncio
import time
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional, Union

from haystack import Document, Pipeline
from haystack.components.builders import ChatPromptBuilder
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.components.generators.utils import print_streaming_chunk
from haystack.components.joiners.document_joiner import DocumentJoiner
from haystack.dataclasses import ChatMessage
from haystack.tools import Tool
from haystack.utils import Secret

from chat2rag.config import CONFIG
from chat2rag.logger import get_logger
from chat2rag.pipelines.base import BasePipeline
from chat2rag.pipelines.document import DocumentSearchPipeline
from chat2rag.pipelines.funciton import FunctionPipeline

logger = get_logger(__name__)
# from chat2rag.telemetry import setup_telemetry

# setup_telemetry()


class RAGPipeline(BasePipeline):
    """
    RAGPipeline is a pipeline that uses a retriever to retrieve documents from a document store,
    and a generator to generate a response to a query.
    """

    @staticmethod
    @lru_cache(maxsize=32)
    def _create_doc_pipeline(index: str) -> DocumentSearchPipeline:
        """
        Cache document pipeline
        """
        logger.debug(f"Creating new document pipeline for index: {index}")
        return DocumentSearchPipeline(index)

    @staticmethod
    @lru_cache(maxsize=32)
    def _create_function_pipeline(intention_model: str) -> FunctionPipeline:
        """
        Cache function pipeline
        """
        logger.debug(f"Creating new function pipeline for model: {intention_model}")
        return FunctionPipeline(intention_model)

    def __init__(
        self,
        qdrant_index: Union[str, List[str]],
        intention_model: str = CONFIG.DEFAULT_INTENTION_MODEL,
        generator_model: str = CONFIG.DEFAULT_GENERATOR_MODEL,
        stream_callback: Callable = print_streaming_chunk,
    ):
        """
        Initialize RAG pipeline

        Args:
            qdrant_index: The index name(s) for document retrieval
            intention_model: The model to use for intention recognition
            generator_model: The model to use for response generation
            stream_callback: Callback function for streaming responses
        """

        # 转换索引为列表并创建文档检索管道
        qdrant_list = (
            [qdrant_index] if isinstance(qdrant_index, str) else (qdrant_index or [])
        )
        self.doc_pipeline = [
            self._create_doc_pipeline(qdrant) for qdrant in qdrant_list
        ]

        # 创建函数调用管道
        self.func_pipeline = self._create_function_pipeline(intention_model)

        # 保存基本配置
        self.intention_model = intention_model
        self.generator_model = generator_model
        self._stream_callback = stream_callback

        # 初始化管道
        self.pipeline = self._initialize_pipeline()
        super().__init__()

    def _initialize_pipeline(self):
        """
        Initialize the RAG pipeline

        Returns:
            Pipeline: The initialized Haystack pipeline
        """
        logger.debug("Initialize RAG pipeline...")
        try:
            pipeline = Pipeline()
            prompt_builder = ChatPromptBuilder(
                variables=["query", "documents", "func_response"]
            )

            generator = OpenAIChatGenerator(
                model=self.generator_model,
                api_key=Secret.from_env_var("OPENAI_API_KEY"),
                api_base_url=CONFIG.OPENAI_BASE_URL,
                streaming_callback=self._stream_callback,
            )
            pipeline.add_component("doc_joiner", DocumentJoiner())
            pipeline.add_component("prompt_builder", prompt_builder)
            pipeline.add_component("generator", generator)
            pipeline.connect("doc_joiner.documents", "prompt_builder.documents")
            pipeline.connect("prompt_builder.prompt", "generator")

            logger.debug("Initialize RAG pipeline successfully")
            return pipeline

        except Exception as e:
            logger.error(f"Initialize RAG pipeline falied: {e}", exc_info=True)
            raise

    def warm_up(self):
        """
        Warm up the RAG pipeline by loading necessary models and resources
        """
        logger.debug("Warm up the RAG pipeline...")
        try:
            self.pipeline.warm_up()
            logger.debug("RAG pipeline warm up successfully")

        except Exception as e:
            logger.error("Failed to warm up RAG pipeline: %s", e)
            raise

    async def _process_documents(
        self, documents_list: List[Document], stream_handler: Optional[Any] = None
    ) -> None:
        """
        Process document retrieval results and update stream handler if needed

        Args:
            documents_list: List of retrieved documents
            stream_handler: Optional stream handler for progress updates
        """
        if stream_handler and hasattr(stream_handler, "set_doc_info"):
            stream_handler.set_doc_info(len(documents_list))
            stream_handler.start()

    async def run(
        self,
        query: str,
        tools: List[Tool] = [],
        prompt_template: str = None,
        messages: List[ChatMessage] = None,
        top_k: int = None,
        score_threshold: float = None,
        generation_kwargs: Dict[str, Any] = {},
    ) -> Dict[str, Any]:
        """
        Run the RAG pipeline with the given query

        Args:
            query: The user query
            prompt_template: The template for response generation
            messages: Previous chat messages for context
            top_k: Maximum number of documents to retrieve
            score_threshold: Minimum similarity score for document retrieval
            generation_kwargs: Additional parameters for the generator

        Returns:
            Dict[str, Any]: Pipeline results including the generated response
        """
        start_time = time.time()
        logger.info(f"Running RAG pipeline with query: <{query}>...")

        if not prompt_template:
            prompt_template = CONFIG.RAG_PROMPT_TEMPLATE
            logger.debug("Using default rag prompt template")
        if not top_k:
            top_k = CONFIG.TOP_K
            logger.debug("Using default top_k")
        if not score_threshold:
            score_threshold = CONFIG.SCORE_THRESHOLD
            logger.debug("Using default score_threshold")

        # 并发执行文档检索和函数调用
        tasks = [
            *[
                pipeline.run(query, top_k, score_threshold)
                for pipeline in self.doc_pipeline
            ],
            self.func_pipeline.run(query, messages, tools=tools),
        ]

        all_results = await asyncio.gather(*tasks)

        # 分离函数调用结果和文档检索结果
        func_results = all_results[-1]  # 最后一个是函数调用结果
        doc_results = all_results[:-1]  # 前面的都是文档检索结果

        # 合并所有文档
        documents_list = []
        for result in doc_results:
            if result and "retriever" in result and "documents" in result["retriever"]:
                documents_list.extend(result["retriever"]["documents"])

        # 获取流式处理处理器
        stream_handler = (
            self._stream_callback.__self__
            if hasattr(self._stream_callback, "__self__")
            else None
        )
        await self._process_documents(documents_list, stream_handler)

        # 处理函数调用结果
        func_response = ""
        for func_message in func_results["tool_invoker"]["tool_messages"]:
            if func_message.tool_call_result:
                func_response += func_message.tool_call_result.result

        # 构建问题模板
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
        prompt_template = [
            ChatMessage.from_system(prompt_template),
            *messages,
            ChatMessage.from_user(question_template),
        ]

        # 运行生成管道并返回结果
        result = self.pipeline.run(
            data={
                "doc_joiner": {"documents": documents_list},
                "prompt_builder": {
                    "template": prompt_template,
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


if __name__ == "__main__":
    rag_pipeline = RAGPipeline(
        qdrant_index="test",
        intention_model=CONFIG.DEFAULT_INTENTION_MODEL,
        generator_model=CONFIG.DEFAULT_GENERATOR_MODEL,
        stream_callback=print_streaming_chunk,
    )
    asyncio.run(
        rag_pipeline.run(
            query="今天天气怎么样",
        )
    )
