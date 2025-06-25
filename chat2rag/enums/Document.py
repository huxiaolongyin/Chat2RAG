from enum import Enum


class DocumentType(str, Enum):
    """
    The type of document.

    QA Pair matches questions and answers for retrieval.
    QUESTION only matches questions and is generally used for precise answers.
    """

    QA_PAIR = "qa_pair"
    QUESTION = "question"
