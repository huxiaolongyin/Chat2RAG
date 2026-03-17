from datetime import datetime
from typing import List

from pydantic import Field, computed_field

from chat2rag.core.enums import DocumentType, FileStatus, FileType

from .base import BaseSchema


class CollectionData(BaseSchema):
    """单个知识库集合的响应模型"""

    collection_name: str = Field(..., description="知识库名称", examples=["测试数据"])
    status: str = Field(..., description="知识库状态", examples=["green"])
    documents_count: int = Field(..., description="知识条数", examples=[100])
    embedding_size: int = Field(..., description="嵌入编码的维度", examples=[1024])
    distance: str = Field(..., description="距离的计算方式", examples=["Cosine"])


class CollectionPaginatedData(BaseSchema):
    """知识库集合分页数据 - 兼容collectionList字段格式"""

    collection_list: List[CollectionData] = Field(
        default_factory=list, description="知识库列表"
    )
    total: int = Field(default=0, ge=0, description="总记录数")
    current: int = Field(default=1, ge=1, description="当前页码")
    size: int = Field(default=20, ge=1, description="每页条数")

    @computed_field
    @property
    def pages(self) -> int:
        """总页数"""
        return (self.total + self.size - 1) // self.size if self.total > 0 else 0

    @classmethod
    def create(
        cls,
        items: List[CollectionData],
        total: int,
        current: int = 1,
        size: int = 20,
    ) -> "CollectionPaginatedData":
        """创建知识库集合分页数据"""
        return cls(collection_list=items, total=total, current=current, size=size)


class SourceLocation(BaseSchema):
    """来源位置 - 精确定位文档内容"""

    file_path: str
    page_num: int | None = None
    section: str | None = None
    paragraph_num: int | None = None
    line_num: int | None = None
    table_name: str | None = None
    url: str | None = None

    def __str__(self) -> str:
        """生成可读的位置信息"""
        parts = [self.file_path]
        if self.page_num:
            parts.append(f"第{self.page_num}页")
        if self.section:
            parts.append(f"[{self.section}]")
        if self.paragraph_num:
            parts.append(f"段落{self.paragraph_num}")
        return " - ".join(parts)


class DocumentData(BaseSchema):
    """统一的文档模型"""

    doc_type: DocumentType
    content: str = Field(..., description="用于向量化的内容")
    answer: str | None = Field(None, description="直接回复内容（QUESTION类型使用）")
    source: SourceLocation = Field(..., description="数据来源")
    retrieval_count: int = Field(default=0, description="检索次数")
    create_time: datetime = Field(default_factory=datetime.now)
    update_time: datetime = Field(default_factory=datetime.now)
    version: int = Field(default=1, description="版本号")
    parent_doc_id: str | None = Field(None, description="父文档ID（用于分块）")
    chunk_index: int | None = Field(None, description="分块索引")
    external_id: str | None = Field(None, description="外部ID（用于指定文档ID）")


class ReindexResult(BaseSchema):
    """重新索引结果"""

    points_count: int = Field(..., description="重新索引的文档数量")
    backup_file: str | None = Field(None, description="备份文件路径")


class FileData(BaseSchema):
    """文件数据"""

    id: int = Field(..., description="文件ID")
    collection_name: str = Field(..., description="所属知识库")
    filename: str = Field(..., description="文件名")
    file_type: FileType = Field(..., description="文件类型")
    file_size: int = Field(default=0, description="文件大小(字节)")
    status: FileStatus = Field(..., description="状态")
    version: int = Field(default=1, description="当前版本")
    chunk_count: int = Field(default=0, description="分块数量")
    parse_config: dict | None = Field(None, description="解析配置")
    error_message: str | None = Field(None, description="错误信息")
    create_time: datetime | None = Field(None, description="创建时间")
    update_time: datetime | None = Field(None, description="更新时间")


class FileVersionData(BaseSchema):
    """文件版本数据"""

    id: int = Field(..., description="版本ID")
    version: int = Field(..., description="版本号")
    file_size: int = Field(default=0, description="文件大小(字节)")
    change_note: str | None = Field(None, description="变更说明")
    chunk_count: int = Field(default=0, description="分块数量")
    parse_config: dict | None = Field(None, description="解析配置")
    create_time: datetime | None = Field(None, description="创建时间")


class ChunkData(BaseSchema):
    """知识分块数据"""

    id: str = Field(..., description="分块ID")
    content: str = Field(..., description="内容")
    chunk_index: int | None = Field(None, description="分块索引")
