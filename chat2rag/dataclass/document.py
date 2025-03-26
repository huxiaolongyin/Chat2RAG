from dataclasses import dataclass


@dataclass
class QADocument:
    """
    问题和答案的文档
    """

    question: str
    answer: str
