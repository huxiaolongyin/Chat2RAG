from tortoise import fields

from .base import BaseModel, TimestampMixin


class Tenant(BaseModel, TimestampMixin):
    """租户模型"""

    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100, description="租户名称")
    code = fields.CharField(max_length=50, unique=True, description="租户编码")
    logo = fields.TextField(null=True, description="租户Logo")
    contact_name = fields.CharField(max_length=50, null=True, description="联系人")
    contact_phone = fields.CharField(max_length=20, null=True, description="联系电话")
    status = fields.IntField(default=1, description="状态: 0-禁用, 1-启用")
    expire_time = fields.DatetimeField(null=True, description="过期时间")
    remark = fields.TextField(null=True, description="备注")

    class Meta:
        table = "tenants"

    def __str__(self):
        return self.name
