from chat2rag.core.crud import CRUDBase
from chat2rag.models import SensitivedCategory, SensitiveWords
from chat2rag.schemas.sensitive import (
    SensitiveWordCategoryCreate,
    SensitiveWordCategoryUpdate,
    SensitiveWordCreate,
    SensitiveWordUpdate,
)


class SensitiveCategoryService(
    CRUDBase[
        SensitivedCategory, SensitiveWordCategoryCreate, SensitiveWordCategoryUpdate
    ]
):
    def __init__(self):
        super().__init__(SensitivedCategory)


class SensitiveService(
    CRUDBase[SensitiveWords, SensitiveWordCreate, SensitiveWordUpdate]
):
    def __init__(self):
        super().__init__(SensitiveWords)

    async def get_active_sensitive_list(self):
        sensitive_words = await self.model.filter(is_active=True).all()
        return [item.word for item in sensitive_words]
