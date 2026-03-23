from fastapi import APIRouter, Depends

from chat2rag.core.deps import get_current_user, require_permissions
from chat2rag.models import Tenant
from chat2rag.schemas.base import BaseResponse, PaginatedResponse, PaginationParams
from chat2rag.schemas.tenant import TenantCreate, TenantResponse, TenantUpdate

router = APIRouter()


@router.get("", response_model=PaginatedResponse[TenantResponse])
async def get_tenants(pagination: PaginationParams = Depends()):
    """获取租户列表"""
    total = await Tenant.all().count()
    tenants = (
        await Tenant.all()
        .offset(pagination.offset)
        .limit(pagination.limit)
        .order_by("-id")
    )
    return PaginatedResponse.create(
        items=[await t.to_dict() for t in tenants],
        total=total,
        current=pagination.current,
        size=pagination.size,
    )


@router.get("/{tenant_id}", response_model=BaseResponse[TenantResponse])
async def get_tenant(tenant_id: int):
    """获取租户详情"""
    tenant = await Tenant.filter(id=tenant_id).first()
    if not tenant:
        return BaseResponse.error(msg="租户不存在", code="4004", http_status=404)
    return BaseResponse(data=await tenant.to_dict())


@router.post(
    "",
    response_model=BaseResponse[TenantResponse],
    dependencies=[require_permissions("system:tenant:create")],
)
async def create_tenant(data: TenantCreate):
    """创建租户"""
    existing = await Tenant.filter(code=data.code).first()
    if existing:
        return BaseResponse.error(msg="租户编码已存在", code="4001", http_status=400)

    tenant = Tenant(
        name=data.name,
        code=data.code,
        logo=data.logo,
        contact_name=data.contact_name,
        contact_phone=data.contact_phone,
        status=data.status,
        expire_time=data.expire_time,
        remark=data.remark,
    )
    await tenant.save()
    return BaseResponse(data=await tenant.to_dict())


@router.put(
    "/{tenant_id}",
    response_model=BaseResponse[TenantResponse],
    dependencies=[require_permissions("system:tenant:update")],
)
async def update_tenant(tenant_id: int, data: TenantUpdate):
    """更新租户"""
    tenant = await Tenant.filter(id=tenant_id).first()
    if not tenant:
        return BaseResponse.error(msg="租户不存在", code="4004", http_status=404)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tenant, field, value)

    await tenant.save()
    return BaseResponse(data=await tenant.to_dict())


@router.delete(
    "/{tenant_id}",
    response_model=BaseResponse,
    dependencies=[require_permissions("system:tenant:delete")],
)
async def delete_tenant(tenant_id: int):
    """删除租户"""
    tenant = await Tenant.filter(id=tenant_id).first()
    if not tenant:
        return BaseResponse.error(msg="租户不存在", code="4004", http_status=404)

    from chat2rag.models import User

    user_count = await User.filter(tenant_id=tenant_id).count()
    if user_count > 0:
        return BaseResponse.error(
            msg="租户下存在用户，不能删除", code="4003", http_status=403
        )

    await tenant.delete()
    return BaseResponse(msg="删除成功")
