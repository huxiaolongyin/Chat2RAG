from datetime import datetime
from typing import Optional

from pydantic import Field

from .base import BaseSchema, IDMixin, TimestampMixin


class TenantBase(BaseSchema):
    name: str = Field(..., max_length=100, description="租户名称")
    code: str = Field(..., max_length=50, description="租户编码")
    logo: Optional[str] = Field(None, description="租户Logo")
    contact_name: Optional[str] = Field(None, max_length=50, description="联系人")
    contact_phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    status: int = Field(default=1, ge=0, le=1, description="状态: 0-禁用, 1-启用")
    expire_time: Optional[datetime] = Field(None, description="过期时间")
    remark: Optional[str] = Field(None, description="备注")


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=100, description="租户名称")
    logo: Optional[str] = Field(None, description="租户Logo")
    contact_name: Optional[str] = Field(None, max_length=50, description="联系人")
    contact_phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    status: Optional[int] = Field(None, ge=0, le=1, description="状态")
    expire_time: Optional[datetime] = Field(None, description="过期时间")
    remark: Optional[str] = Field(None, description="备注")


class TenantResponse(TenantBase, IDMixin, TimestampMixin):
    pass
