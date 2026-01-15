from chat2rag.core.crud import CRUDBase
from chat2rag.models import Metric
from chat2rag.schemas.metric import MetricCreate, MetricUpdate


class MetricService(CRUDBase[Metric, MetricCreate, MetricUpdate]):
    def __init__(self):
        super().__init__(Metric)


metric_service = MetricService()
