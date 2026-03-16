import asyncio
import re
from typing import List, Tuple

from chat2rag.config import CONFIG
from chat2rag.core.logger import get_logger
from chat2rag.schemas.document import DocumentData
from chat2rag.utils.llm_client import LLMClient

logger = get_logger(__name__)

BATCH_SIZE = 5
MAX_RETRIES = 2

DOCUMENT_SUMMARY_PROMPT = """请根据以下文档内容，提取文档标题和生成一段简短的摘要（不超过100字）。

文档内容：
{content}

请按以下格式输出：
标题：xxx
摘要：xxx"""

CHUNK_CONTEXT_PROMPT = """请为以下文档片段分别生成简短的上下文说明（每个50字以内），说明该片段在文档中的作用和内容主题。

文档标题：{title}
文档摘要：{summary}

片段列表：
{chunks_text}

请按以下格式输出，每个片段一行，严格保持序号对应：
[1] 上下文说明1
[2] 上下文说明2
..."""


class ContextualRetrieval:
    """Contextual Retrieval 实现：为每个分块生成独立上下文"""

    def __init__(self, batch_size: int = BATCH_SIZE, max_retries: int = MAX_RETRIES):
        self.llm_client = LLMClient()
        self.batch_size = batch_size
        self.max_retries = max_retries

    async def extract_document_summary(
        self, content: str, max_chars: int = 2000
    ) -> Tuple[str, str]:
        """
        提取文档标题和摘要

        Returns:
            (title, summary) - 标题和摘要
        """
        if not content or not content.strip():
            return "未知文档", ""

        truncated = content[:max_chars].strip()
        if len(truncated) < 50:
            return "未知文档", truncated

        try:
            messages = [
                {
                    "role": "user",
                    "content": DOCUMENT_SUMMARY_PROMPT.format(content=truncated),
                }
            ]
            response = await self.llm_client.acall_llm(
                messages=messages,
                model=CONFIG.PROCESS_MODEL,
                max_tokens=200,
                temperature=0.3,
                extra_log="Document Summary",
            )

            title = "未知文档"
            summary = ""

            title_match = re.search(r"标题[：:]\s*(.+?)(?:\n|$)", response)
            if title_match:
                title = title_match.group(1).strip()

            summary_match = re.search(r"摘要[：:]\s*(.+?)(?:\n|$)", response, re.DOTALL)
            if summary_match:
                summary = summary_match.group(1).strip()

            logger.info(f"提取文档标题: {title}, 摘要: {summary[:50]}...")
            return title, summary

        except Exception as e:
            logger.exception(f"提取文档摘要失败: {e}")
            return "未知文档", ""

    async def generate_chunk_contexts_batch(
        self,
        title: str,
        summary: str,
        chunks: List[str],
    ) -> List[str | None]:
        """
        批量生成分块上下文

        Args:
            title: 文档标题
            summary: 文档摘要
            chunks: 分块内容列表

        Returns:
            上下文列表，失败的位置为 None
        """
        if not chunks:
            return []

        contexts: List[str | None] = [None] * len(chunks)

        for batch_start in range(0, len(chunks), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(chunks))
            batch_chunks = chunks[batch_start:batch_end]

            chunks_text = "\n".join(
                f"[{i+1}] {chunk[:300]}..." if len(chunk) > 300 else f"[{i+1}] {chunk}"
                for i, chunk in enumerate(batch_chunks)
            )

            prompt = CHUNK_CONTEXT_PROMPT.format(
                title=title,
                summary=summary,
                chunks_text=chunks_text,
            )

            for retry in range(self.max_retries + 1):
                try:
                    messages = [{"role": "user", "content": prompt}]
                    response = await self.llm_client.acall_llm(
                        messages=messages,
                        model=CONFIG.PROCESS_MODEL,
                        max_tokens=300,
                        temperature=0.3,
                        extra_log=f"Chunk Context Batch {batch_start}",
                    )

                    batch_contexts = self._parse_contexts(response, len(batch_chunks))
                    for i, ctx in enumerate(batch_contexts):
                        contexts[batch_start + i] = ctx

                    if retry > 0:
                        logger.info(f"批次 {batch_start} 重试成功")
                    break

                except Exception as e:
                    if retry < self.max_retries:
                        logger.warning(
                            f"批次 {batch_start} 第 {retry+1} 次失败，重试: {e}"
                        )
                        await asyncio.sleep(1)
                    else:
                        logger.error(f"批次 {batch_start} 上下文生成失败，跳过: {e}")

        success_count = sum(1 for c in contexts if c is not None)
        logger.info(f"上下文生成完成: {success_count}/{len(chunks)} 成功")
        return contexts

    def _parse_contexts(self, response: str, expected_count: int) -> List[str | None]:
        """解析 LLM 返回的上下文列表"""
        contexts: List[str | None] = [None] * expected_count
        pattern = r"\[(\d+)\]\s*(.+?)(?=\[\d+\]|$)"

        matches = re.findall(pattern, response, re.DOTALL)
        for idx_str, context in matches:
            try:
                idx = int(idx_str) - 1
                if 0 <= idx < expected_count:
                    contexts[idx] = context.strip()
            except ValueError:
                continue

        return contexts

    @staticmethod
    def apply_context_to_chunk(
        content: str,
        context: str | None,
        title: str | None = None,
        section: str | None = None,
    ) -> str:
        """
        将上下文应用到分块内容

        Args:
            content: 原始分块内容
            context: 生成的上下文
            title: 文档标题（可选）
            section: 章节信息（可选）

        Returns:
            追加了上下文的分块内容
        """
        if not context:
            return content

        parts = []
        if title:
            parts.append(f"文档：{title}")
        if section:
            parts.append(f"章节：{section}")

        if parts:
            header = " > ".join(parts)
            return f"【{header}】{context}\n\n{content}"
        else:
            return f"【{context}】\n\n{content}"
