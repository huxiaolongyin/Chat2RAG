from datetime import datetime
from typing import List, Optional

from pydantic import Field

from .base import BaseSchema, IDMixin, TimestampMixin


class UserBase(BaseSchema):
    username: str = Field(..., max_length=50, description="用户名")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    avatar: Optional[str] = Field(None, description="头像URL")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")
    status: int = Field(default=1, ge=0, le=1, description="状态: 0-禁用, 1-启用")


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    tenant_id: Optional[int] = Field(None, description="租户ID，为空则使用当前租户")
    role_ids: Optional[List[int]] = Field(None, description="角色ID列表")


class UserUpdate(BaseSchema):
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    avatar: Optional[str] = Field(None, description="头像URL")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")
    status: Optional[int] = Field(None, ge=0, le=1, description="状态")
    role_ids: Optional[List[int]] = Field(None, description="角色ID列表")


class UserPasswordUpdate(BaseSchema):
    old_password: str = Field(..., min_length=6, description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=50, description="新密码")


class UserResponse(UserBase, IDMixin, TimestampMixin):
    tenant_id: int = Field(..., description="租户ID")
    is_superuser: bool = Field(default=False, description="是否超级管理员")
    last_login_time: Optional[datetime] = Field(None, description="最后登录时间")
    last_login_ip: Optional[str] = Field(None, description="最后登录IP")


class UserDetailResponse(UserResponse):
    roles: List[str] = Field(default_factory=list, description="角色编码列表")
    role_names: List[str] = Field(default_factory=list, description="角色名称列表")


class UserRoleUpdate(BaseSchema):
    role_ids: List[int] = Field(..., description="角色ID列表")
