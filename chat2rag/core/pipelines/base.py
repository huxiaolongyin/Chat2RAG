from abc import ABC, abstractmethod
from typing import Generic, Type, TypeVar

from chat2rag.logger import get_logger

logger = get_logger(__name__)

# Define type variables
T = TypeVar("T")


class BasePipeline(Generic[T], ABC):
    def __init__(self):
        self._initialized = False
        self.pipeline: Type[T] = None

    async def initialize(self):
        """异步初始化方法"""
        if not self._initialized:
            await self._prepare_async_resources()
            self.pipeline = self._initialize_pipeline()
            self.warm_up()
            self._initialized = True
        return self

    async def _prepare_async_resources(self):
        """准备异步资源，子类可重写"""
        pass

    def __str__(self):
        return str(self.pipeline)

    def __repr__(self):
        return str(self.pipeline)

    @abstractmethod
    def _initialize_pipeline(self):
        """
        Initialize RAG pipeline
        """
        pass

    def warm_up(self):
        """
        Warm up the RAG pipeline by loading necessary models and resources
        """
        try:
            self.pipeline.warm_up()
            logger.debug(
                f"The {self.__class__.__name__} has been warmed up successfully"
            )
        except Exception as e:
            logger.error(
                f"Failed to warm up the {self.__class__.__name__}. Failure reason: %s",
                e,
            )
            raise

    @abstractmethod
    async def run(self, *args, **kwargs):
        """
        Run the RAG pipeline
        """
        pass
