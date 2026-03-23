from enum import Enum
from typing import List, Optional

from pydantic import Field

from .base import BaseSchema, IDMixin, TimestampMixin


class PermissionType(str, Enum):
    MENU = "menu"
    API = "api"
    BUTTON = "button"


class PermissionBase(BaseSchema):
    name: str = Field(..., max_length=50, description="权限名称")
    code: str = Field(..., max_length=100, description="权限编码")
    type: PermissionType = Field(default=PermissionType.MENU, description="权限类型")
    path: Optional[str] = Field(None, max_length=255, description="路由路径/API路径")
    component: Optional[str] = Field(None, max_length=255, description="组件路径")
    icon: Optional[str] = Field(None, max_length=50, description="图标")
    sort: int = Field(default=0, description="排序")
    status: int = Field(default=1, ge=0, le=1, description="状态: 0-禁用, 1-启用")
    visible: bool = Field(default=True, description="是否可见")
    cache: bool = Field(default=False, description="是否缓存")
    remark: Optional[str] = Field(None, description="备注")


class PermissionCreate(PermissionBase):
    parent_id: Optional[int] = Field(None, description="父级权限ID")


class PermissionUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=50, description="权限名称")
    path: Optional[str] = Field(None, max_length=255, description="路由路径/API路径")
    component: Optional[str] = Field(None, max_length=255, description="组件路径")
    icon: Optional[str] = Field(None, max_length=50, description="图标")
    sort: Optional[int] = Field(None, description="排序")
    status: Optional[int] = Field(None, ge=0, le=1, description="状态")
    visible: Optional[bool] = Field(None, description="是否可见")
    cache: Optional[bool] = Field(None, description="是否缓存")
    remark: Optional[str] = Field(None, description="备注")


class PermissionResponse(PermissionBase, IDMixin, TimestampMixin):
    parent_id: Optional[int] = Field(None, description="父级权限ID")


class PermissionTreeResponse(PermissionResponse):
    children: List["PermissionTreeResponse"] = Field(
        default_factory=list, description="子权限列表"
    )
