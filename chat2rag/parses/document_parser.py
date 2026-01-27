from abc import ABC, abstractmethod
from typing import List

import pandas as pd

from chat2rag.core.enums import DocumentType
from chat2rag.core.logger import get_logger
from chat2rag.schemas.document import DocumentData, SourceLocation

logger = get_logger(__name__)


class DocumentParser(ABC):
    """文档解析器基类"""

    @abstractmethod
    async def parse(self, file_path: str) -> List[DocumentData]:
        """解析文档"""
        pass


class PDFParser(DocumentParser):
    """PDF解析器"""

    async def parse(self, file_path: str) -> List[DocumentData]:
        documents = []
        # 使用PyPDF2或pdfplumber
        chunks = []
        # 提取文本、表格、图片等
        # 按页面或段落分块
        return documents


class WordParser(DocumentParser):
    """Word解析器"""

    async def parse(self, file_path: str) -> List[DocumentData]:
        documents = []
        # 使用python-docx
        chunks = []
        # 提取段落、表格、标题等
        # 保留文档结构
        return documents


class MarkdownParser(DocumentParser):
    """Markdown解析器"""

    async def parse(self, file_path: str) -> List[DocumentData]:
        documents = []
        # 解析Markdown结构
        chunks = []
        # 按标题级别分块
        return documents


class QAPairParser(DocumentParser):
    """问答对解析器"""

    async def parse(self, file_path: str) -> List[DocumentData]:
        documents = []
        # 读取文件
        try:
            if file_path.endswith(".csv"):
                try:
                    df = pd.read_csv(file_path, sep=";")
                except:
                    df = pd.read_csv(file_path, sep=",")
            elif file_path.endswith(".xlsx"):
                df = pd.read_excel(file_path)
            else:
                raise ValueError(f"不支持的文件格式: {file_path}")

        except Exception as e:
            raise ValueError(f"读取文件失败: {str(e)}")

        # 验证是否存在表头
        required_columns = ["问题", "答案"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"缺少必要的列: {missing_columns}")

        # 遍历每一行创建DocumentData对象
        for idx, row in df.iterrows():
            try:
                chunks = [
                    DocumentData(
                        doc_type=DocumentType.QUESTION,
                        source=SourceLocation(file_path=file_path),
                        content=row["问题"],
                        answer=row["答案"],
                    ),
                    DocumentData(
                        doc_type=DocumentType.QA_PAIR,
                        source=SourceLocation(file_path=file_path),
                        content=f"{row['问题']}:{row['答案']}",
                    ),
                ]
                documents.extend(chunks)

            except Exception as e:
                # 可选：记录错误行并继续处理
                logger.warning(f"处理第 {idx} 行时出错: {str(e)}")
                continue

        return documents
