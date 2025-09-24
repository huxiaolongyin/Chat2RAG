import asyncio
from time import perf_counter
from typing import Any, Callable, Dict, List, Union

from haystack import Pipeline
from haystack.components.builders import ChatPromptBuilder
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.components.generators.utils import print_streaming_chunk
from haystack.components.joiners.document_joiner import DocumentJoiner
from haystack.dataclasses import ChatMessage
from haystack.utils import Secret

from chat2rag.config import CONFIG
from chat2rag.logger import logger
from chat2rag.pipelines.base import BasePipeline
from chat2rag.pipelines.document import DocumentSearchPipeline
from chat2rag.utils.pipeline_cache import create_pipeline


class RAGPipeline(BasePipeline):
    def __init__(
        self,
        qdrant_index: Union[str, List[str]],
        intention_model: str = "Qwen/Qwen2.5-14B-Instruct",
        generator_model: str = "Qwen/Qwen2.5-32B-Instruct",
        stream_callback: Callable = print_streaming_chunk,
    ):
        try:
            qdrant_index = (
                [qdrant_index]
                if isinstance(qdrant_index, str)
                else (qdrant_index or [])
            )
            # 直接使用列表推导式创建 pipeline
            self.doc_pipeline = (
                [
                    create_pipeline(DocumentSearchPipeline, index)
                    for index in qdrant_index
                ]
                if qdrant_index
                else []
            )
            self.qdrant_index = qdrant_index
            self.intention_model = intention_model
            self.generator_model = generator_model
            self._stream_callback = stream_callback
            super().__init__()

        except Exception as e:
            logger.error(f"The initialization of the RAG pipeline was failed: {e}")
            raise e

    def _initialize_pipeline(self):
        """
        Initialize RAG pipeline
        """
        try:
            pipeline = Pipeline()
            prompt_builder = ChatPromptBuilder(
                variables=[
                    "query",
                    "qdrant_index",
                    "documents",
                    "func_response",
                ]
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

            logger.info("Initialize RAG pipeline successfully")
            return pipeline

        except Exception as e:
            logger.error(f"Initialize RAG pipeline falied: {e}", exc_info=True)
            raise e

    async def run(
        self,
        query: str,
        rag_prompt_template: str = CONFIG.RAG_PROMPT_TEMPLATE,
        top_k: int = CONFIG.TOP_K,
        score_threshold: float = CONFIG.SCORE_THRESHOLD,
        messages: List[ChatMessage] = [],
        generation_kwargs: Dict[str, Any] = {},
        streaming_callback: Callable = print_streaming_chunk,
        start_time: float = 0,
        *args,
        **kwargs,
    ) -> Dict[str, Any]:
        try:
            # 并发执行文档检索和函数调用
            doc_tasks = [
                pipeline.run(query, top_k, score_threshold)
                for pipeline in self.doc_pipeline
            ]
            doc_result = await asyncio.gather(*doc_tasks)

            # 处理文档结果
            documents_list = [
                doc for result in doc_result for doc in result["retriever"]["documents"]
            ]

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
                        "query": query,
                    },
                    "generator": {
                        "generation_kwargs": generation_kwargs,
                        "streaming_callback": streaming_callback,
                    },
                },
                include_outputs_from=["doc_joiner"],
            )

            answer = str(result["generator"]["replies"][0].text).replace("\n", "")
            logger.info(
                f"RAG pipeline ran successfully. Query: <{query}>; Answer: <{answer}>; Cost {perf_counter() - start_time:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"RAG pipeline ran failed: {e}")
            raise e
