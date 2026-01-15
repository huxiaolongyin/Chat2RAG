from typing import List

from pydantic import Field, computed_field

from .base import BaseSchema


class collectionItemResponse(BaseSchema):
    """单个知识库集合的响应模型"""

    collection_name: str = Field(..., description="知识库名称", examples=["测试数据"])
    status: str = Field(..., description="知识库状态", examples=["green"])
    documents_count: int = Field(..., description="知识条数", examples=[100])
    embedding_size: int = Field(..., description="嵌入编码的维度", examples=[1024])
    distance: str = Field(..., description="距离的计算方式", examples=["Cosine"])


class collectionPaginatedData(BaseSchema):
    """知识库集合分页数据 - 兼容collectionList字段格式"""

    collection_list: List[collectionItemResponse] = Field(
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
        items: List[collectionItemResponse],
        total: int,
        current: int = 1,
        size: int = 20,
    ) -> "collectionPaginatedData":
        """创建知识库集合分页数据"""
        return cls(collection_list=items, total=total, current=current, size=size)
