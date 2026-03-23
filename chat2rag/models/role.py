from tortoise import fields

from .base import BaseModel, TimestampMixin


class Role(BaseModel, TimestampMixin):
    """角色模型"""

    id = fields.IntField(primary_key=True)
    tenant = fields.ForeignKeyField(
        "app_system.Tenant",
        related_name="roles",
        on_delete=fields.CASCADE,
        null=True,
        description="所属租户，为空表示系统角色",
    )
    name = fields.CharField(max_length=50, description="角色名称")
    code = fields.CharField(max_length=50, description="角色编码")
    description = fields.TextField(null=True, description="角色描述")
    is_system = fields.BooleanField(default=False, description="是否系统内置角色")
    status = fields.IntField(default=1, description="状态: 0-禁用, 1-启用")
    sort = fields.IntField(default=0, description="排序")

    class Meta:
        table = "roles"
        unique_together = ("tenant", "code")

    def __str__(self):
        return self.name


class UserRole(BaseModel):
    """用户角色关联表"""

    id = fields.IntField(primary_key=True)
    user = fields.ForeignKeyField(
        "app_system.User", related_name="user_roles", on_delete=fields.CASCADE
    )
    role = fields.ForeignKeyField(
        "app_system.Role", related_name="role_users", on_delete=fields.CASCADE
    )

    class Meta:
        table = "user_roles"
        unique_together = ("user", "role")


class RolePermission(BaseModel):
    """角色权限关联表"""

    id = fields.IntField(primary_key=True)
    role = fields.ForeignKeyField(
        "app_system.Role", related_name="role_permissions", on_delete=fields.CASCADE
    )
    permission = fields.ForeignKeyField(
        "app_system.Permission",
        related_name="permission_roles",
        on_delete=fields.CASCADE,
    )

    class Meta:
        table = "role_permissions"
        unique_together = ("role", "permission")
