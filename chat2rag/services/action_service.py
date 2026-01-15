from chat2rag.core.crud import CRUDBase
from chat2rag.exceptions import ValueAlreadyExist
from chat2rag.models import RobotAction
from chat2rag.schemas.action import RobotActionCreate, RobotActionUpdate


class RobotActionService(CRUDBase[RobotAction, RobotActionCreate, RobotActionUpdate]):
    def __init__(self):
        super().__init__(RobotAction)

    async def create(self, obj_in: RobotActionCreate, exclude=None) -> RobotAction:
        if await self.model.filter(name=obj_in.name).exists():
            raise ValueAlreadyExist("该动作名称已存在")
        if await self.model.filter(code=obj_in.code).exists():
            raise ValueAlreadyExist("该动作代码已存在")

        return await super().create(obj_in, exclude)

    async def update(self, id: int, obj_in: RobotActionUpdate, exclude=None) -> RobotAction:
        await self.get(id)
        if obj_in.name and await self.model.filter(name=obj_in.name).exclude(id=id).exists():
            raise ValueAlreadyExist("该动作名称已存在")
        if obj_in.code and await self.model.filter(code=obj_in.code).exclude(id=id).exists():
            raise ValueAlreadyExist("该动作代码已存在")

        return await super().update(id, obj_in, exclude)

    async def get_active_action_list(self):
        """Return CODE list"""
        actions = await self.model.filter(is_active=True).all()
        return [action.name for action in actions]

    async def get_code_by_name(self, name: str = "") -> RobotAction:
        return await self.model.filter(name=name).first()


robot_action_service = RobotActionService()
