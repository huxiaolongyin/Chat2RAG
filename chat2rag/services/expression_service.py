from chat2rag.core.crud import CRUDBase
from chat2rag.core.exceptions import ValueAlreadyExist
from chat2rag.models import RobotExpression
from chat2rag.schemas.expression import RobotExpressionCreate, RobotExpressionUpdate


class RobotExpressionService(CRUDBase[RobotExpression, RobotExpressionCreate, RobotExpressionUpdate]):
    def __init__(self):
        super().__init__(RobotExpression)

    async def create(self, obj_in: RobotExpressionCreate, exclude=None) -> RobotExpression:
        if await self.model.filter(name=obj_in.name).exists():
            raise ValueAlreadyExist("该表情名称已存在")
        if await self.model.filter(code=obj_in.code).exists():
            raise ValueAlreadyExist("该表情代码已存在")

        return await super().create(obj_in, exclude)

    async def update(self, id: int, obj_in: RobotExpressionUpdate, exclude=None) -> RobotExpression:
        await self.get(id)
        if obj_in.name and await self.model.filter(name=obj_in.name).exclude(id=id).exists():
            raise ValueAlreadyExist("该表情名称已存在")
        if obj_in.code and await self.model.filter(code=obj_in.code).exclude(id=id).exists():
            raise ValueAlreadyExist("该表情代码已存在")

        return await super().update(id, obj_in, exclude)

    async def get_active_expression_list(self):
        """Return CODE list"""
        expressions = await self.model.filter(is_active=True).all()
        return [expression.name for expression in expressions]

    async def get_code_by_name(self, name: str = "") -> RobotExpression:
        return await self.model.filter(name=name).first()


robot_expression_service = RobotExpressionService()
