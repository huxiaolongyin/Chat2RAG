from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, Tuple, Type, TypeVar, Union

from pydantic import BaseModel
from sqlalchemy import and_, asc, desc, func, inspect, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import Query, Session

from chat2rag.logger import get_logger

logger = get_logger(__name__)

# 定义泛型类型变量
ModelType = TypeVar("ModelType", bound=DeclarativeMeta)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class Paginator:
    """分页结果类"""

    def __init__(
        self, items: List[Any], total: int, page: int = 1, page_size: int = 20
    ):
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size
        self.pages = (total + page_size - 1) // page_size if total > 0 else 0
        self.has_next = page < self.pages
        self.has_prev = page > 1

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "items": [item.to_dict() for item in self.items],
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "pages": self.pages,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
        }


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    高级ORM基类，提供丰富的数据库操作功能
    """

    def __init__(self, model: Type[ModelType]):
        """
        初始化服务

        Args:
            model: SQLAlchemy模型类
        """
        self.model = model
        self.model_pk = self._get_primary_key()

    def _get_primary_key(self) -> str:
        """获取模型的主键字段名"""
        mapper = inspect(self.model)
        for column in mapper.columns:
            if column.primary_key:
                return column.name
        return "id"  # 默认主键名

    @contextmanager
    def safe_db_transaction(self, db: Session):
        """
        安全的数据库事务上下文管理器

        使用方式:
            with service.safe_db_transaction(db) as tx:
                tx.add(obj)
        """
        try:
            yield db
            db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"数据库事务错误: {str(e)}")
            raise

    def create(
        self, db: Session, obj_in: Union[CreateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """创建新记录"""
        if isinstance(obj_in, dict):
            obj_in_data = obj_in
            db_obj = self.model(**obj_in_data)
        elif isinstance(obj_in, BaseModel):
            obj_in_data = obj_in.model_dump()
            db_obj = self.model(**obj_in_data)
        # 检查是否是 SQLAlchemy 模型实例
        elif isinstance(obj_in, self.model.__class__) or hasattr(obj_in, "__table__"):
            db_obj = obj_in
        else:
            raise TypeError("不支持的类型")

        with self.safe_db_transaction(db) as tx:
            tx.add(db_obj)
            tx.flush()
            tx.refresh(db_obj)

        return db_obj

    def create_multi(
        self, db: Session, objs_in: List[Union[CreateSchemaType, Dict[str, Any]]]
    ) -> List[ModelType]:
        """批量创建记录"""
        db_objs = []

        for obj_in in objs_in:
            obj_in_data = (
                obj_in.model_dump() if isinstance(obj_in, BaseModel) else obj_in
            )
            db_objs.append(self.model(**obj_in_data))

        with self.safe_db_transaction(db) as tx:
            tx.add_all(db_objs)
            tx.flush()

        return db_objs

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """通过ID获取记录"""
        return (
            db.query(self.model)
            .filter(getattr(self.model, self.model_pk) == id)
            .first()
        )

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: List[Any] = None,
        order_by: List[Any] = None,
    ) -> List[ModelType]:
        """获取多条记录"""
        query = db.query(self.model)

        if filters:
            query = query.filter(*filters)

        if order_by:
            query = query.order_by(*order_by)

        return query.offset(skip).limit(limit).all()

    def get_paginated(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 20,
        filters: List[Any] = None,
        order_by: List[Any] = None,
    ) -> Tuple[List[Type[ModelType]], int]:
        """获取分页记录"""

        query = db.query(self.model)

        if filters:
            query = query.filter(*filters)

        # 计算总数
        total = query.count()

        # 应用排序
        if order_by:
            query = query.order_by(*order_by)

        # 应用分页
        skip = (page - 1) * page_size
        items = query.offset(skip).limit(page_size).all()

        return items, total

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
    ) -> ModelType:
        """更新记录"""
        obj_data = db_obj.__dict__.copy()

        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field in obj_data:
            if field in update_data and field != self.model_pk:
                setattr(db_obj, field, update_data[field])

        with self.safe_db_transaction(db) as tx:
            tx.add(db_obj)
            tx.flush()
            tx.refresh(db_obj)

        return db_obj

    def delete(self, db: Session, *, id: Any) -> Optional[ModelType]:
        """删除记录"""
        obj = self.get(db, id)
        if obj:
            with self.safe_db_transaction(db) as tx:
                tx.delete(obj)

        return obj

    def delete_multi(self, db: Session, *, ids: List[Any]) -> int:
        """批量删除记录"""
        with self.safe_db_transaction(db) as tx:
            count = (
                tx.query(self.model)
                .filter(getattr(self.model, self.model_pk).in_(ids))
                .delete(synchronize_session=False)
            )

        return count

    def count(self, db: Session, filters: List[Any] = None) -> int:
        """计数"""
        query = db.query(func.count(getattr(self.model, self.model_pk)))

        if filters:
            query = query.filter(*filters)

        return query.scalar()

    def exists(self, db: Session, id: Any) -> bool:
        """检查记录是否存在"""
        return db.query(
            db.query(self.model)
            .filter(getattr(self.model, self.model_pk) == id)
            .exists()
        ).scalar()

    def filter_by(self, **kwargs) -> List[Any]:
        """构建简单的等值过滤条件"""
        filters = []
        for field, value in kwargs.items():
            if hasattr(self.model, field):
                filters.append(getattr(self.model, field) == value)
        return filters

    def order_by_field(self, field_name: str, descending: bool = False) -> Any:
        """构建排序条件"""
        if not hasattr(self.model, field_name):
            raise ValueError(f"字段 {field_name} 不存在于模型 {self.model.__name__} 中")

        field = getattr(self.model, field_name)
        return desc(field) if descending else asc(field)

    def between_dates(
        self, field_name: str, start_date: datetime, end_date: datetime
    ) -> Any:
        """构建日期范围过滤条件"""
        if not hasattr(self.model, field_name):
            raise ValueError(f"字段 {field_name} 不存在于模型 {self.model.__name__} 中")

        field = getattr(self.model, field_name)
        return and_(field >= start_date, field <= end_date)

    def build_query(
        self,
        db: Session,
        filters: List[Any] = None,
        order_by: List[Any] = None,
        group_by: List[Any] = None,
        joins: List[Tuple[Any, Any]] = None,
    ) -> Query:
        """构建高级查询"""
        query = db.query(self.model)

        # 应用连接
        if joins:
            for entity, join_condition in joins:
                query = query.join(entity, join_condition)

        # 应用过滤
        if filters:
            query = query.filter(*filters)

        # 应用分组
        if group_by:
            query = query.group_by(*group_by)

        # 应用排序
        if order_by:
            query = query.order_by(*order_by)

        return query
