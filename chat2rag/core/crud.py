from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel
from pydantic.main import IncEx
from tortoise.expressions import Q
from tortoise.models import Model

from chat2rag.core.exceptions import ValueNoExist

ModelType = TypeVar("ModelType", bound=Model)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: type[ModelType]):
        self.model = model

    async def get(self, id: int) -> ModelType:
        """
        获取单个数据
        Args:
            id: 主键ID
        Returns:
            单个数据
        """
        obj = await self.model.get_or_none(id=id)
        if not obj:
            raise ValueNoExist()
        return obj

    async def get_list(
        self,
        page: int,
        page_size: int,
        search: Q = Q(),
        order: list[str] | None = None,
        prefetch: Optional[List[str]] = None,
        distinct: bool = False,
    ) -> tuple[int, list[ModelType]]:
        """
        获取列表数据
        Args:
            page: 页码
            page_size: 每页数量
            search: 查询条件
            order: 排序
            prefetch: 预加载
        Returns:
            总数, 列表数据
        """

        # 过滤
        query = self.model.filter(search)

        # 去重
        if distinct:
            query = query.distinct()

        # 查询总数 - 先获取所有 ID，然后计数
        # 这样确保 count 和 all() 的逻辑一致
        try:
            ids = await query.values_list("id", flat=True)
        except Exception:
            # 如果没有id字段，则查找包含"id"字符的第一个字段
            field_names = list(self.model._meta.fields_map.keys())
            id_field = next(
                (field for field in field_names if "id" in field.lower()),
                field_names[0] if field_names else "id",
            )
            ids = await query.values_list(id_field, flat=True)
        total = len(ids)

        # 去重（用于后续的 all() 查询）
        if distinct:
            query = query.distinct()

        if total == 0:
            return total, []

        # 分页查询
        query = query.limit(page_size).offset((page - 1) * page_size)

        # 关联预加载
        if prefetch:
            query = query.prefetch_related(*prefetch)

        # 排序
        order = order or []
        if order:
            query = query.order_by(*order)

        return total, await query.all()

    async def create(
        self,
        obj_in: CreateSchemaType,
        exclude: IncEx = None,
    ) -> ModelType:
        """
        创建数据
        Args:
            obj_in: 创建数据模型
            exclude: 排除字段
            prefetch: 预加载
        Returns:
            创建后的数据
        """
        if isinstance(obj_in, dict):
            obj_dict = obj_in
        else:
            obj_dict = obj_in.model_dump(exclude_unset=True, exclude_none=True, exclude=exclude)
        obj: ModelType = self.model(**obj_dict)
        await obj.save()
        return obj

    async def update(
        self,
        id: int,
        obj_in: UpdateSchemaType,
        exclude: IncEx = None,
    ) -> ModelType:
        """
        更新数据
        Args:
            id: 主键ID
            obj_in: 更新数据模型
            exclude: 排除字段
        Returns:
            更新后的数据
        """
        if isinstance(obj_in, dict):
            obj_dict = obj_in
        else:
            obj_dict = obj_in.model_dump(exclude_unset=True, exclude_none=True, exclude=exclude)
        obj = await self.get(id=id)
        obj = obj.update_from_dict(obj_dict)
        await obj.save()
        return obj

    async def remove(self, id: int) -> None:
        """
        删除数据
        Args:
            id: 主键ID
        """
        obj = await self.get(id=id)
        await obj.delete()
