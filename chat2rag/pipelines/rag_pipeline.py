import asyncio
from datetime import datetime
from time import perf_counter
from typing import Any, Awaitable, Callable, Dict, List, Union

from haystack import AsyncPipeline
from haystack.components.builders import ChatPromptBuilder
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.components.joiners.document_joiner import DocumentJoiner
from haystack.dataclasses import ChatMessage
from haystack.utils import Secret

from chat2rag.config import CONFIG
from chat2rag.core.logger import get_logger
from chat2rag.utils.merge_kwargs import recursive_tuple_to_dict
from chat2rag.utils.pipeline_cache import create_pipeline

from .base import BasePipeline
from .document import DocumentSearchPipeline

logger = get_logger(__name__)


class RAGPipeline(BasePipeline[AsyncPipeline]):
    def __init__(
        self,
        # qdrant_index: Union[str, List[str]],
        intention_model: str = "Qwen/Qwen2.5-14B-Instruct",
        generator_model: str = "Qwen/Qwen2.5-32B-Instruct",
        api_base_url: str = "",
        api_key: str = "",
    ):

        self._intention_model = intention_model
        self._generator_model = generator_model
        self._api_base_url = api_base_url
        self._api_key = api_key

        super().__init__()

    def _initialize_pipeline(self):
        """
        Initialize RAG pipeline
        """
        try:
            pipeline = AsyncPipeline()
            prompt_builder = ChatPromptBuilder(
                variables=[
                    "query",
                    "qdrant_index",
                    "documents",
                    "func_response",
                ]
            )
            generator = OpenAIChatGenerator(
                model=self._generator_model,
                api_key=Secret.from_token(self._api_key),
                api_base_url=self._api_base_url,
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
        top_k: int = CONFIG.TOP_K,
        score_threshold: float = CONFIG.SCORE_THRESHOLD,
        messages: List[ChatMessage] = [],
        generation_kwargs: Dict[str, Any] = {},
        streaming_callback: Callable[[Any], Awaitable[None]] = None,
        start_time: float = 0,
        qdrant_index: Union[str, List[str]] = "",
        *args,
        **kwargs,
    ) -> Dict[str, Any]:
        try:
            qdrant_index = [qdrant_index] if isinstance(qdrant_index, str) else (qdrant_index or [])

            self.doc_pipeline = (
                [await create_pipeline(DocumentSearchPipeline, index) for index in qdrant_index] if qdrant_index else []
            )
            # 并发执行文档检索和函数调用
            doc_tasks = [pipeline.run(query, top_k, score_threshold) for pipeline in self.doc_pipeline]
            doc_result = await asyncio.gather(*doc_tasks)

            # 处理文档结果
            documents_list = [doc for result in doc_result for doc in result["retriever"]["documents"]]

            # 构建问题模板
            # current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # question_template = f"""
            # 问题：{{{{query}}}}；
            # 当前日期时间：{current_date}
            # 文档参考内容(移除所有URL和网页地址再输出)：
            # {{% if documents %}}
            #     {{% for doc in documents %}}
            #         content: {{{{ doc.content }}}} score: {{{{ doc.score }}}}
            #     {{% endfor %}}
            # {{% else %}}
            #     None
            # {{% endif %}}
            # """
            # prompt_template = [
            #     *messages,
            #     ChatMessage.from_user(question_template),
            # ]

            # 构建并返回结果
            result = await self.pipeline.run_async(
                data={
                    "doc_joiner": {"documents": documents_list},
                    "prompt_builder": {
                        "template": messages,
                        "qdrant_index": qdrant_index,
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
