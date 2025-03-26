from abc import ABC, abstractmethod


class BasePipeline(ABC):
    def __init__(self):
        self.warm_up()

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

    @abstractmethod
    def warm_up(self):
        """
        Warm up the RAG pipeline by loading necessary models and resources
        """
        pass

    @abstractmethod
    async def run(self, *args, **kwargs):
        """
        Run the RAG pipeline
        """
        pass
