from typing import List, Optional

from pydantic import Field

from .base import BaseSchema, IDMixin, TimestampMixin


class RoleBase(BaseSchema):
    name: str = Field(..., max_length=50, description="角色名称")
    code: str = Field(..., max_length=50, description="角色编码")
    description: Optional[str] = Field(None, description="角色描述")
    status: int = Field(default=1, ge=0, le=1, description="状态: 0-禁用, 1-启用")
    sort: int = Field(default=0, description="排序")


class RoleCreate(RoleBase):
    tenant_id: Optional[int] = Field(None, description="租户ID，为空表示系统角色")
    permission_ids: Optional[List[int]] = Field(None, description="权限ID列表")


class RoleUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=50, description="角色名称")
    description: Optional[str] = Field(None, description="角色描述")
    status: Optional[int] = Field(None, ge=0, le=1, description="状态")
    sort: Optional[int] = Field(None, description="排序")
    permission_ids: Optional[List[int]] = Field(None, description="权限ID列表")


class RoleResponse(RoleBase, IDMixin, TimestampMixin):
    tenant_id: Optional[int] = Field(None, description="租户ID")
    is_system: bool = Field(default=False, description="是否系统内置角色")


class RoleDetailResponse(RoleResponse):
    permissions: List[str] = Field(default_factory=list, description="权限编码列表")
    permission_names: List[str] = Field(
        default_factory=list, description="权限名称列表"
    )


class RolePermissionUpdate(BaseSchema):
    permission_ids: List[int] = Field(..., description="权限ID列表")
