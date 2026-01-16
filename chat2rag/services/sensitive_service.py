from chat2rag.core.crud import CRUDBase
from chat2rag.core.exceptions import ValueAlreadyExist
from chat2rag.models import SensitivedCategory, SensitiveWords
from chat2rag.schemas.sensitive import (
    SensitiveWordCategoryCreate,
    SensitiveWordCategoryUpdate,
    SensitiveWordCreate,
    SensitiveWordUpdate,
)


class SensitiveCategoryService(CRUDBase[SensitivedCategory, SensitiveWordCategoryCreate, SensitiveWordCategoryUpdate]):
    def __init__(self):
        super().__init__(SensitivedCategory)

    async def create(self, obj_in: SensitiveWordCategoryCreate, exclude=None):
        if await self.model.filter(name=obj_in.name).exists():
            raise ValueAlreadyExist("该分类已存在")
        return await super().create(obj_in, exclude)

    async def update(self, id, obj_in: SensitiveWordCategoryUpdate, exclude=None):
        if await self.model.filter(name=obj_in.name).exists():
            raise ValueAlreadyExist("该分类已存在")
        return await super().update(id, obj_in, exclude)


class SensitiveService(CRUDBase[SensitiveWords, SensitiveWordCreate, SensitiveWordUpdate]):
    def __init__(self):
        super().__init__(SensitiveWords)

    async def create(self, obj_in: SensitiveWordCreate, exclude=None):
        if await self.model.filter(word=obj_in.word).exists():
            raise ValueAlreadyExist("该敏感词已存在")
        return await super().create(obj_in, exclude)

    async def update(self, id, obj_in: SensitiveWordUpdate, exclude=None):
        if await self.model.filter(word=obj_in.word).exists():
            raise ValueAlreadyExist("该敏感词已存在")
        return await super().update(id, obj_in, exclude)

    async def get_active_sensitive_list(self):
        sensitive_words = await self.model.filter(is_active=True).all()
        return [item.word for item in sensitive_words]


sensitive_category_service = SensitiveCategoryService()
sensitive_service = SensitiveService()
