from chat2rag.core.crud import CRUDBase
from chat2rag.models import RobotExpression
from chat2rag.schemas.expression import RobotExpressionCreate, RobotExpressionUpdate


class RobotExpressionService(
    CRUDBase[RobotExpression, RobotExpressionCreate, RobotExpressionUpdate]
):
    def __init__(self):
        super().__init__(RobotExpression)

    async def get_active_expression_list(self):
        """Return CODE list"""
        expressions = await self.model.filter(is_active=True).all()
        return [expression.code for expression in expressions]
