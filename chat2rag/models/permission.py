from enum import Enum

from tortoise import fields

from .base import BaseModel, TimestampMixin


class PermissionType(str, Enum):
    """权限类型"""

    MENU = "menu"
    API = "api"
    BUTTON = "button"


class Permission(BaseModel, TimestampMixin):
    """权限模型"""

    id = fields.IntField(primary_key=True)
    parent = fields.ForeignKeyField(
        "app_system.Permission",
        related_name="children",
        null=True,
        on_delete=fields.CASCADE,
        description="父级权限",
    )
    name = fields.CharField(max_length=50, description="权限名称")
    code = fields.CharField(max_length=100, unique=True, description="权限编码")
    type = fields.CharEnumField(
        PermissionType, default=PermissionType.MENU, description="权限类型"
    )
    path = fields.CharField(max_length=255, null=True, description="路由路径/API路径")
    component = fields.CharField(max_length=255, null=True, description="组件路径")
    icon = fields.CharField(max_length=50, null=True, description="图标")
    sort = fields.IntField(default=0, description="排序")
    status = fields.IntField(default=1, description="状态: 0-禁用, 1-启用")
    visible = fields.BooleanField(default=True, description="是否可见")
    cache = fields.BooleanField(default=False, description="是否缓存")
    remark = fields.TextField(null=True, description="备注")

    class Meta:
        table = "permissions"

    def __str__(self):
        return self.name
