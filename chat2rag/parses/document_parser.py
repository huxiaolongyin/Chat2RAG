import asyncio
import os
import re
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import List, Tuple

import pandas as pd
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
from docling_core.types.doc.document import PictureItem, SectionHeaderItem, TextItem
from docx import Document
from docx.document import Document as DocumentObject

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

    doc_converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_cls=StandardPdfPipeline, backend=PyPdfiumDocumentBackend
            )
        },
    )

    def __init__(self, max_chars: int = 600, overlap: int = 100):
        if overlap >= max_chars:
            raise ValueError(
                f"overlap ({overlap}) must be less than max_chars ({max_chars})"
            )
        self._max_chars = max_chars
        self._overlap = overlap

    def _split_by_chars(self, text: str, max_chars: int, overlap: int) -> List[str]:
        text = text.strip()
        if not text:
            return []
        if len(text) <= max_chars:
            return [text]

        chunks: List[str] = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(text_len, start + max_chars)
            chunks.append(text[start:end])

            if end >= text_len:
                break
            start = end - overlap

        return chunks

    def _flush(
        self, file_path: str, page_num: int, result: List[DocumentData], buf: list[str]
    ):
        if buf:
            content = "".join(buf).strip()
            if len(content) <= self._max_chars:
                result.append(
                    DocumentData(
                        doc_type=DocumentType.WORD,
                        content=content,
                        source=SourceLocation(
                            file_path=file_path,
                            page_num=page_num,
                        ),
                        answer=None,
                        parent_doc_id=None,
                        chunk_index=None,
                        external_id=None,
                    )
                )
            else:
                chunks = self._split_by_chars(content, self._max_chars, self._overlap)
                for chunk in chunks:
                    result.append(
                        DocumentData(
                            doc_type=DocumentType.WORD,
                            content=chunk,
                            source=SourceLocation(
                                file_path=file_path,
                                page_num=page_num,
                            ),
                            answer=None,
                            parent_doc_id=None,
                            chunk_index=None,
                            external_id=None,
                        )
                    )
            buf.clear()

    async def parse(self, file_path: str) -> List[DocumentData]:
        result: List[DocumentData] = []
        buf: list[str] = []
        page_no = 0

        doc = self.doc_converter.convert(file_path)

        for item, *_ in doc.document.iterate_items():
            try:
                page_no = item.prov[0].page_no
            except:
                page_no = 0

            if isinstance(item, PictureItem):
                continue

            if isinstance(item, SectionHeaderItem):
                self._flush(
                    file_path=file_path, page_num=page_no, result=result, buf=buf
                )
                buf.append(item.text)
                buf.append("\n")
                continue

            if isinstance(item, TextItem):
                buf.append(item.text)
                continue

        self._flush(file_path=file_path, page_num=page_no, result=result, buf=buf)
        return result


class WordParser(DocumentParser):
    """
    Word文档解析器，实现三阶段分块策略：
    1. 按标题层级分块
    2. 按章节编号分块
    3. 按字符长度分块（带重叠）
    """

    # ---------- 规则：识别“一、二、(一)、（二）...”等特殊标识 ----------
    _CN_NUM = "一二三四五六七八九十百千万零〇"
    _SECTION_PATTERNS = [
        # 一级：一、 二、 三、
        rf"^(?P<mark>[{_CN_NUM}]+)、\s*(?P<title>.*)$",
        # 二级：(一) (二) ... / （一） （二）...
        rf"^(?P<mark>[\(（][{_CN_NUM}]+[\)）])\s*(?P<title>.*)$",
        # 可选：1. 2. / 1、2、（如果你也想要）
        # r"^(?P<mark>\d+)[\.、]\s*(?P<title>.*)$",
    ]
    _SECTION_RES = [re.compile(p) for p in _SECTION_PATTERNS]

    DEFAULT_MAX_CHARS = 600
    DEFAULT_OVERLAP = 100

    def __init__(
        self,
        max_chars: int = DEFAULT_MAX_CHARS,
        overlap: int = DEFAULT_OVERLAP,
        *,
        preserve_hierarchy: bool = True,  # 是否保留层级信息
    ):
        if overlap >= max_chars:
            raise ValueError(
                f"overlap ({overlap}) must be less than max_chars ({max_chars})"
            )
        self._max_chars = max_chars
        self._overlap = overlap
        self._preserve_hierarchy = preserve_hierarchy

    async def parse(self, file_path: str) -> List[DocumentData]:
        """解析入口，统一错误处理"""
        self._validate_file(file_path)

        return await asyncio.to_thread(self._parse_sync, file_path)

    def _heading_level(self, style_name: str) -> int | None:
        """规则：识别“文章标题”(Word 标题样式)"""
        # 兼容英文 Heading 1 / 中文 标题 1
        for prefix in ("Heading ", "标题 "):
            if style_name.startswith(prefix):
                try:
                    return int(style_name[len(prefix) :].strip())
                except ValueError:
                    return None
        return None

    def _validate_file(self, file_path: str) -> None:
        """文件校验"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        if not file_path.lower().endswith(".docx"):
            raise ValueError(f"Expected .docx file, got: {file_path}")

    def _match_section_mark(self, line: str) -> Tuple[str, str] | None:
        """匹配章节编号标记，返回 (标记, 标题) 或 None"""
        stripped = line.strip()
        for pattern in self._SECTION_RES:
            match = pattern.match(stripped)
            if match:
                mark = match.group("mark")
                title = (match.group("title") or "").strip()
                return mark, title
        return None

    def _split_by_chars(self, text: str, max_chars: int, overlap: int) -> List[str]:
        """按字符长度分块，支持重叠

        Args:
            text: 待分割文本
            max_chars: 每块最大字符数
            overlap: 块之间的重叠字符数

        Returns:
            分割后的文本块列表
        """
        text = text.strip()
        if not text:
            return []
        if len(text) <= max_chars:
            return [text]

        chunks: List[str] = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(text_len, start + max_chars)
            chunks.append(text[start:end])

            if end >= text_len:
                break
            start = end - overlap

        return chunks

    def _parse_sync(self, file_path: str) -> List[DocumentData]:
        """同步解析逻辑"""
        with self._open_document(file_path) as doc:
            paragraphs = self._extract_paragraphs(doc)

        chunks = self._chunk_by_hierarchy(paragraphs, file_path)
        return self._chunk_by_size(chunks, file_path)

    @contextmanager
    def _open_document(self, file_path: str):
        """安全地打开文档"""
        try:
            doc = Document(file_path)
            yield doc
        finally:
            # python-docx 没有标准 close 方法
            pass

    def _extract_paragraphs(self, doc: DocumentObject) -> List[Tuple[str, int | None]]:
        """提取段落及标题层级"""
        paragraphs = []
        for para in doc.paragraphs:
            text = (para.text or "").strip()
            if not text:
                continue
            level = self._heading_level(para.style.name if para.style else "")
            paragraphs.append((text, level))
        return paragraphs

    def _chunk_by_hierarchy(
        self, paragraphs: List[Tuple[str, int | None]], file_path: str
    ) -> List[DocumentData]:
        """按层级分块，标题作为后续内容的头部"""
        chunks: List[DocumentData] = []
        heading_stack: List[Tuple[int, str]] = []
        content_buffer: List[str] = []
        current_section: str = ""  # 当前章节路径

        for text, level in paragraphs:
            # 检查是否匹配章节编号标记（一、二、(一)、（二）等）
            section_match = self._match_section_mark(text)

            if level is not None:
                # 遇到标题：先输出之前缓存的内容
                if content_buffer:
                    chunks.append(
                        self._make_chunk(
                            content_buffer, file_path, section=current_section or None
                        )
                    )
                    content_buffer.clear()

                # 更新标题栈
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                heading_stack.append((level, text))

                # 更新当前章节路径
                current_section = " > ".join(h[1] for h in heading_stack)
            elif section_match:
                # 遇到章节编号标记：先输出之前缓存的内容
                if content_buffer:
                    chunks.append(
                        self._make_chunk(content_buffer, file_path, section=None)
                    )
                    content_buffer.clear()

                # 将章节标题加入 buffer（不设置 section，因为章节编号已在内容中）
                content_buffer.append(text)
            else:
                # 如果 buffer 为空且有章节，添加章节前缀到内容
                if not content_buffer and current_section:
                    content_buffer.append(f"[{current_section}]")
                content_buffer.append(text)

        # 刷新最后的内容
        if content_buffer:
            chunks.append(
                self._make_chunk(
                    content_buffer, file_path, section=current_section or None
                )
            )

        return chunks

    def _make_chunk(
        self, lines: List[str], file_path: str, section: str = None
    ) -> DocumentData:
        """创建文档块"""
        return DocumentData(
            doc_type=DocumentType.WORD,
            content="\n".join(lines).strip(),
            source=SourceLocation(file_path=file_path, section=section),
        )

    def _chunk_by_size(
        self, chunks: List[DocumentData], file_path: str
    ) -> List[DocumentData]:
        """按大小二次分块"""
        final_chunks: List[DocumentData] = []

        for chunk in chunks:
            if len(chunk.content) <= self._max_chars:
                final_chunks.append(chunk)
            else:
                parts = self._split_by_chars(
                    chunk.content, self._max_chars, self._overlap
                )
                for part in parts:
                    final_chunks.append(
                        DocumentData(
                            doc_type=DocumentType.WORD,
                            content=part,
                            source=SourceLocation(file_path=file_path),
                        )
                    )

        return final_chunks


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
                logger.exception(f"Failed to process row {idx}")
                continue

        return documents


class TSVParser(DocumentParser):
    """TSV解析器 - 格式: id\tcontent"""

    async def parse(self, file_path: str) -> List[DocumentData]:
        documents = []
        try:
            df = pd.read_csv(file_path, sep="\t", header=None, names=["id", "content"])
        except Exception as e:
            raise ValueError(f"读取文件失败: {str(e)}")

        for idx, row in df.iterrows():
            if pd.isna(row["content"]) or str(row["content"]).strip() == "":
                continue
            documents.append(
                DocumentData(
                    doc_type=DocumentType.TSV,
                    source=SourceLocation(file_path=file_path),
                    content=str(row["content"]),
                    external_id=str(row["id"]),
                )
            )
        return documents


if __name__ == "__main__":
    parse = WordParser()
    result = asyncio.run(parse.parse("temp/放射性食管炎宣教.docx"))
    for i in result:
        print(i)
        print(i)
