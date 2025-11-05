from tortoise import fields

from .base import BaseModel, TimestampMixin


class FlowData(BaseModel, TimestampMixin):
    """流程数据 - 主记录"""

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255)
    desc = fields.TextField(null=True)
    current_version = fields.IntField(default=1, null=True)  # 当前最新版本
    flow_json = fields.JSONField(null=True)

    class Meta:
        table = "flow_data"


# class FlowDataHistory(Model):
#     """流程数据历史版本"""
#
#     id = fields.IntField(primary_key=True)
#     flow_data = fields.ForeignKeyField("models.FlowData", related_name="histories")
#     version = fields.IntField()
#     flow_json = fields.JSONField()
#
#     class Meta:
#         table = "flow_data_history"
#         unique_together = ("flow_data", "version")
