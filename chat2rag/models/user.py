from tortoise import fields

from .base import BaseModel, TimestampMixin


class User(BaseModel, TimestampMixin):
    """用户模型"""

    id = fields.IntField(primary_key=True)
    tenant = fields.ForeignKeyField(
        "app_system.Tenant",
        related_name="users",
        on_delete=fields.CASCADE,
        description="所属租户",
    )
    username = fields.CharField(max_length=50, description="用户名")
    password = fields.CharField(max_length=255, description="密码")
    phone = fields.CharField(max_length=20, null=True, description="手机号")
    nickname = fields.CharField(max_length=50, null=True, description="昵称")
    avatar = fields.TextField(null=True, description="头像URL")
    email = fields.CharField(max_length=100, null=True, description="邮箱")
    status = fields.IntField(default=1, description="状态: 0-禁用, 1-启用")
    is_superuser = fields.BooleanField(default=False, description="是否超级管理员")
    last_login_time = fields.DatetimeField(null=True, description="最后登录时间")
    last_login_ip = fields.CharField(max_length=50, null=True, description="最后登录IP")

    class Meta:
        table = "users"
        unique_together = (("tenant", "username"), ("tenant", "phone"))

    def __str__(self):
        return self.username

    async def to_dict(self, include_fields=None, exclude_fields=None, m2m=False):
        result = await super().to_dict(include_fields, exclude_fields, m2m)
        if "password" not in (exclude_fields or []):
            result.pop("password", None)
        return result
