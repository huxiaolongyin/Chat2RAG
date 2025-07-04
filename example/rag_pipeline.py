import asyncio

from haystack.components.generators.utils import print_streaming_chunk

from chat2rag.config import CONFIG
from chat2rag.pipelines.rag import RAGPipeline

rag_pipeline = RAGPipeline(
    qdrant_index=["test"],
    model=CONFIG.DEFAULT_MODEL,
    stream_callback=print_streaming_chunk,
)
asyncio.run(rag_pipeline.run(query="今天福州天气怎么样", tools=["maps_weather"]))
