from chat2rag.core.crud import CRUDBase
from chat2rag.models import RobotAction
from chat2rag.schemas.action import RobotActionCreate, RobotActionUpdate


class RobotActionService(CRUDBase[RobotAction, RobotActionCreate, RobotActionUpdate]):
    def __init__(self):
        super().__init__(RobotAction)

    async def get_active_action_list(self):
        """Return CODE list"""
        actions = await self.model.filter(is_active=True).all()
        return [action.code for action in actions]
