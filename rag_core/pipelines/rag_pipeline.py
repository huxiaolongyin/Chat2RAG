import asyncio
from functools import lru_cache
from time import perf_counter
from typing import Any, Callable, Dict, List, Union

from haystack import Pipeline
from haystack.components.builders import ChatPromptBuilder
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.components.generators.utils import print_streaming_chunk
from haystack.components.joiners.document_joiner import DocumentJoiner
from haystack.dataclasses import ChatMessage
from haystack.utils import Secret

from rag_core.config import CONFIG
from rag_core.logging import logger
from rag_core.pipelines.doc_pipeline import DocumentSearchPipeline
from rag_core.pipelines.func_pipeline import FunctionPipeline


class RAGPipeline:
    @staticmethod
    @lru_cache(maxsize=32)
    def _create_doc_pipeline(index: str) -> DocumentSearchPipeline:
        """
        Cache document pipeline
        """
        return DocumentSearchPipeline(index)

    def __init__(
        self,
        qdrant_index: Union[str, List[str]],
        intention_model: str = CONFIG.DEFAULT_INTENTION_MODEL,
        generator_model: str = CONFIG.DEFAULT_GENERATOR_MODEL,
        stream_callback: Callable = print_streaming_chunk,
    ):
        qdrant_index = (
            [qdrant_index] if isinstance(qdrant_index, str) else (qdrant_index or [])
        )
        # 直接使用列表推导式创建 pipeline
        self.doc_pipeline = (
            [self._create_doc_pipeline(index) for index in qdrant_index]
            if qdrant_index
            else []
        )
        self.func_pipeline = FunctionPipeline(intention_model)
        self.qdrant_index = qdrant_index
        self.intention_model = intention_model
        self.generator_model = generator_model
        self._stream_callback = stream_callback
        self._initialize_pipeline()
        self.warm_up()

    def __str__(self):
        return str(self.pipeline)

    def __repr__(self):
        return str(self.pipeline)

    def _create_generator(self) -> Any:
        """
        Creater generator component.
        """
        logger.info(
            f"Initialize generator component with model: {self.generator_model}"
        )

        generator = OpenAIChatGenerator(
            model=self.generator_model,
            api_key=Secret.from_env_var("OPENAI_API_KEY"),
            api_base_url=CONFIG.OPENAI_BASE_URL,
            streaming_callback=self._stream_callback,
        )

        logger.info("OpenAI Generator initialized sucessfully")

        return generator

    def _initialize_pipeline(self):
        """
        Initialize RAG pipeline
        """
        logger.info("Initialize RAG pipeline...")

        try:
            self.pipeline = Pipeline()
            prompt_builder = ChatPromptBuilder(
                variables=[
                    "query",
                    "qdrant_index",
                    "documents",
                    "func_response",
                ]
            )
            generator = self._create_generator()
            self.pipeline.add_component("doc_joiner", DocumentJoiner())
            self.pipeline.add_component("prompt_builder", prompt_builder)
            self.pipeline.add_component("generator", generator)
            self.pipeline.connect("doc_joiner.documents", "prompt_builder.documents")
            self.pipeline.connect("prompt_builder.prompt", "generator")

            logger.info("Initialize RAG pipeline successfully")

        except Exception as e:
            logger.error(f"Initialize RAG pipeline falied: {e}", exc_info=True)
            raise

    def warm_up(self):
        """
        Warm up the RAG pipeline by loading necessary models and resources
        """
        logger.info("Warm up the RAG pipeline")
        self.pipeline.warm_up()
        logger.info("Warm up the RAG pipeline successfully")

    async def _run(
        self,
        query: str,
        rag_prompt_template: str,
        tools: list,
        messages: List[ChatMessage],
        top_k: int,
        score_threshold: float,
        generation_kwargs: Dict[str, Any],
        start=perf_counter(),
    ) -> Dict[str, Any]:

        logger.info(f"Running RAG pipeline with query: <{query}>...")

        # 并发执行文档检索和函数调用
        doc_tasks = [
            pipeline.run(query, top_k, score_threshold, start=start)
            for pipeline in self.doc_pipeline
        ]
        func_result, *doc_result = await asyncio.gather(
            self.func_pipeline.run(query, tools, messages, start=start), *doc_tasks
        )

        # 处理文档结果
        documents_list = [
            doc for result in doc_result for doc in result["retriever"]["documents"]
        ]
        if self._stream_callback != print_streaming_chunk:
            stream_handler = self._stream_callback.__self__
        else:
            stream_handler = None
        if hasattr(stream_handler, "set_doc_info"):
            stream_handler.set_doc_info(len(documents_list))
            stream_handler.start()

        # 处理函数调用结果
        func_response = (
            ",".join(func_result["function_executor"]["response"])
            if "function_executor" in func_result
            else ""
        )

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
            ChatMessage.from_system(rag_prompt_template),
            *messages,
            ChatMessage.from_user(question_template),
        ]

        # 构建并返回结果
        result = self.pipeline.run(
            data={
                "doc_joiner": {"documents": documents_list},
                "prompt_builder": {
                    "template": prompt_template,
                    "qdrant_index": self.qdrant_index,
                    "func_response": func_response,
                    "query": query,
                },
                "generator": {"generation_kwargs": generation_kwargs},
            },
            include_outputs_from=["doc_joiner"],
        )

        answer = str(result["generator"]["replies"][0].content).replace("\n", "")
        logger.info(
            f"RAG pipeline ran successfully. Query: <{query}>; Answer: <{answer}>"
        )

        return result

    def run(
        self,
        query: str,
        rag_prompt_template: str = CONFIG.RAG_PROMPT_TEMPLATE,
        tools: list = None,
        top_k: int = CONFIG.TOP_K,
        score_threshold: float = CONFIG.SCORE_THRESHOLD,
        messages: List[ChatMessage] = [],
        generation_kwargs: Dict[str, Any] = {},
        start=perf_counter(),
    ) -> Dict[str, Any]:
        """
        Running RAG pipeline query

        Args:
            query: 用户查询文本
            tools: 可用工具列表
            rag_prompt_template: 自定义提示模板
            top_k: 返回的最大文档数
            score_threshold: 相似度阈值
            messages: 聊天消息列表

        Returns:
            Dict[str, Any]: 包含生成结果的字典
        """
        # start = perf_counter()
        result = asyncio.run(
            self._run(
                query=query,
                tools=tools,
                rag_prompt_template=rag_prompt_template,
                top_k=top_k,
                score_threshold=score_threshold,
                messages=messages,
                generation_kwargs=generation_kwargs,
                start=start,
            )
        )
        logger.info(f"RAG pipeline query finished, cost {perf_counter() - start:.2f}s")

        return result

    async def arun(
        self,
        query: str,
        tools: list = None,
        rag_prompt_template: str = CONFIG.RAG_PROMPT_TEMPLATE,
        top_k: int = CONFIG.TOP_K,
        score_threshold: float = CONFIG.SCORE_THRESHOLD,
        messages: List[ChatMessage] = [],
        generation_kwargs: Dict[str, Any] = {},
        start=perf_counter(),
    ) -> Dict[str, Any]:
        """
        执行RAG管道查询

        Args:
            query: 用户查询文本
            tools: 可用工具列表
            rag_prompt_template: 自定义提示模板
            top_k: 返回的最大文档数
            score_threshold: 相似度阈值
            messages: 聊天消息列表

        Returns:
            Dict[str, Any]: 包含生成结果的字典
        """
        result = await self._run(
            query=query,
            rag_prompt_template=rag_prompt_template,
            # qdrant_index=self.qdrant_index,
            tools=tools,
            top_k=top_k,
            score_threshold=score_threshold,
            messages=messages,
            generation_kwargs=generation_kwargs,
        )

        logger.info(
            f"Async RAG pipeline query finished, cost {perf_counter() - start:.3f}s"
        )

        return result
