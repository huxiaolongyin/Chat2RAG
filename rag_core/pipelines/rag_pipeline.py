import asyncio
from typing import Callable, Dict, Any, List, Union
from functools import lru_cache
from haystack import Pipeline
from haystack.components.builders import ChatPromptBuilder
from haystack.dataclasses import ChatMessage
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.components.generators.utils import print_streaming_chunk
from haystack.components.joiners.document_joiner import DocumentJoiner
from rag_core.config import CONFIG
from rag_core.utils.logger import logger
from rag_core.pipelines.doc_pipeline import DocumentSearchPipeline
from rag_core.pipelines.func_pipeline import FunctionPipeline
from time import perf_counter


class RAGPipeline:
    @staticmethod
    @lru_cache(maxsize=32)
    def _create_doc_pipeline(index: str) -> DocumentSearchPipeline:
        """缓存管理"""
        return DocumentSearchPipeline(index)

    def __init__(
        self,
        qdrant_index: Union[str, List[str]],
        intention_model: str = "Qwen/Qwen2.5-32B-Instruct",
        generator_model: str = "Qwen/Qwen2.5-32B-Instruct",
        stream_callback: Callable = print_streaming_chunk,
    ):
        qdrant_index = (
            [qdrant_index] if isinstance(qdrant_index, str) else (qdrant_index or [])
        )
        logger.info(
            f"初始化RAG管道，qdrant 索引为: {','.join(qdrant_index)}; 函数调用的模型为：{intention_model}; 生成大模型为：{generator_model}"
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
        self._initialize_pipeline(stream_callback)
        self.warm_up()

    def __str__(self):
        return str(self.pipeline)

    def __repr__(self):
        return str(self.pipeline)

    def _initialize_pipeline(self, stream_callback):
        """初始化检索管道"""
        self.pipeline = Pipeline()

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
            api_key=CONFIG.OPENAI_API_KEY,
            api_base_url=CONFIG.OPENAI_BASE_URL,
            streaming_callback=stream_callback,
        )
        self.pipeline.add_component("doc_joiner", DocumentJoiner())
        self.pipeline.add_component("prompt_builder", prompt_builder)
        self.pipeline.add_component("generator", generator)
        self.pipeline.connect("doc_joiner.documents", "prompt_builder.documents")
        self.pipeline.connect("prompt_builder.prompt", "generator")

    def warm_up(self):
        """预热 RAG 管道，加载必要的模型和资源。"""
        logger.info("预热RAG管道中")
        self.pipeline.warm_up()
        logger.info("RAG管道预热完成")

    async def _run(
        self,
        query: str,
        tools: list,
        template: str,
        top_k: int,
        score_threshold: float,
        messages: List[ChatMessage],
    ) -> Dict[str, Any]:
        # 并发执行文档检索和函数调用
        doc_tasks = [
            pipeline.run(query, top_k, score_threshold)
            for pipeline in self.doc_pipeline
        ]
        func_result, *doc_result = await asyncio.gather(
            self.func_pipeline.run(query, tools, messages), *doc_tasks
        )

        # 处理文档结果
        documents_list = [
            doc for result in doc_result for doc in result["retriever"]["documents"]
        ]

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
        文档参考内容：
        {% for doc in documents %}
        content: {{ doc.content }} score: {{ doc.score }}
        {% endfor %}
        """
        prompt_template = [
            ChatMessage.from_system(template),
            *messages,
            ChatMessage.from_user(question_template),
        ]

        logger.info(
            f"问题：{query}；知识库索引：{self.qdrant_index}； 函数响应：{func_response}; ".replace(
                "\n", ""
            )
        )
        # 构建并返回结果
        return self.pipeline.run(
            data={
                "doc_joiner": {"documents": documents_list},
                "prompt_builder": {
                    "template": prompt_template,
                    "qdrant_index": self.qdrant_index,
                    "func_response": func_response,
                    "query": query,
                },
            }
        )

    def run(
        self,
        query: str,
        tools: list = None,
        template: str = CONFIG.DEFAULT_TEMPLATE,
        top_k: int = CONFIG.TOP_K,
        score_threshold: float = CONFIG.SCORE_THRESHOLD,
        messages: List[ChatMessage] = [],
    ) -> Dict[str, Any]:
        """
        执行RAG管道查询

        Args:
            query: 用户查询文本
            tools: 可用工具列表
            template: 自定义提示模板
            top_k: 返回的最大文档数
            score_threshold: 相似度阈值
            messages: 聊天消息列表

        Returns:
            Dict[str, Any]: 包含生成结果的字典
        """
        start = perf_counter()
        result = asyncio.run(
            self._run(
                query=query,
                tools=tools,
                template=template,
                top_k=top_k,
                score_threshold=score_threshold,
                messages=messages,
            )
        )
        logger.info(f"管道执行完成时间{perf_counter() - start:.2f}s")
        return result

    async def arun(
        self,
        query: str,
        tools: list = None,
        template: str = CONFIG.DEFAULT_TEMPLATE,
        top_k: int = CONFIG.TOP_K,
        score_threshold: float = CONFIG.SCORE_THRESHOLD,
        messages: List[ChatMessage] = [],
    ) -> Dict[str, Any]:
        """
        执行RAG管道查询

        Args:
            query: 用户查询文本
            tools: 可用工具列表
            template: 自定义提示模板
            top_k: 返回的最大文档数
            score_threshold: 相似度阈值
            messages: 聊天消息列表

        Returns:
            Dict[str, Any]: 包含生成结果的字典
        """
        start = perf_counter()
        result = await self._run(
            query=query,
            tools=tools,
            template=template,
            top_k=top_k,
            score_threshold=score_threshold,
            messages=messages,
        )
        logger.info(f"管道执行完成时间{perf_counter() - start:.2f}s")
        return result


if __name__ == "__main__":
    import asyncio
    from rag_core.tools import weather_info, get_current_weather

    tools = [weather_info]
    functions = {
        "weather_tool": get_current_weather,
    }
    pipeline = RAGPipeline("人才集团")

    response = pipeline.run("海外博士后项目支持政策有哪些", tools, functions)
    print(response)
