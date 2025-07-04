from dataclasses import dataclass


@dataclass
class QADocument:
    """
    Question and answer documents
    """

    question: str
    answer: str
