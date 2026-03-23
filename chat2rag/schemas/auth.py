from datetime import datetime
from typing import List, Optional

from pydantic import Field

from .base import BaseSchema


class LoginRequest(BaseSchema):
    username: str = Field(..., max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    tenant_code: Optional[str] = Field(None, max_length=50, description="租户编码")


class SmsCodeRequest(BaseSchema):
    phone: str = Field(..., max_length=20, description="手机号")
    tenant_code: Optional[str] = Field(None, max_length=50, description="租户编码")


class SmsLoginRequest(BaseSchema):
    phone: str = Field(..., max_length=20, description="手机号")
    code: str = Field(..., min_length=4, max_length=6, description="验证码")
    tenant_code: Optional[str] = Field(None, max_length=50, description="租户编码")


class TokenResponse(BaseSchema):
    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="Bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间(秒)")


class LoginResponse(BaseSchema):
    token: TokenResponse = Field(..., description="令牌信息")
    user_id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    nickname: Optional[str] = Field(None, description="昵称")
    avatar: Optional[str] = Field(None, description="头像")
    tenant_id: int = Field(..., description="租户ID")
    tenant_name: str = Field(..., description="租户名称")
    is_superuser: bool = Field(default=False, description="是否超级管理员")
    roles: List[str] = Field(default_factory=list, description="角色编码列表")
    permissions: List[str] = Field(default_factory=list, description="权限编码列表")


class CurrentUserResponse(BaseSchema):
    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    nickname: Optional[str] = Field(None, description="昵称")
    avatar: Optional[str] = Field(None, description="头像")
    email: Optional[str] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, description="手机号")
    tenant_id: int = Field(..., description="租户ID")
    tenant_name: str = Field(..., description="租户名称")
    is_superuser: bool = Field(default=False, description="是否超级管理员")
    status: int = Field(..., description="状态")
    last_login_time: Optional[datetime] = Field(None, description="最后登录时间")
    roles: List[str] = Field(default_factory=list, description="角色编码列表")
    permissions: List[str] = Field(default_factory=list, description="权限编码列表")
