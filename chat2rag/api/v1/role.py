from fastapi import APIRouter, Depends
from tortoise.expressions import Q

from chat2rag.core.deps import get_current_user, get_current_tenant_id
from chat2rag.models import Permission, Role, RolePermission
from chat2rag.schemas.base import BaseResponse, PaginatedResponse, PaginationParams
from chat2rag.schemas.role import (
    RoleCreate,
    RoleResponse,
    RoleUpdate,
    RoleDetailResponse,
)
from chat2rag.services.rbac_service import rbac_service

router = APIRouter()


@router.get("", response_model=PaginatedResponse[RoleResponse])
async def get_roles(
    pagination: PaginationParams = Depends(),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """获取角色列表"""
    query = Role.filter(Q(tenant_id=tenant_id) | Q(tenant_id__isnull=True))
    total = await query.count()
    roles = await query.offset(pagination.offset).limit(pagination.limit).all()
    return PaginatedResponse.create(
        items=[await r.to_dict() for r in roles],
        total=total,
        current=pagination.current,
        size=pagination.size,
    )


@router.get("/{role_id}", response_model=BaseResponse[RoleDetailResponse])
async def get_role(role_id: int, tenant_id: int = Depends(get_current_tenant_id)):
    """获取角色详情"""
    role = await Role.filter(id=role_id).first()
    if not role:
        return BaseResponse.error(msg="角色不存在", code="4004", http_status=404)

    if role.tenant_id is not None and role.tenant_id != tenant_id:
        return BaseResponse.error(msg="无权访问", code="4003", http_status=403)

    permissions = await rbac_service.get_role_permissions(role)
    perm_codes = [p.code for p in permissions]
    perm_names = [p.name for p in permissions]

    role_dict = await role.to_dict()
    role_dict["permissions"] = perm_codes
    role_dict["permission_names"] = perm_names

    return BaseResponse(data=role_dict)


@router.post("", response_model=BaseResponse[RoleResponse])
async def create_role(
    data: RoleCreate,
    tenant_id: int = Depends(get_current_tenant_id),
):
    """创建角色"""
    existing = await Role.filter(tenant_id=tenant_id, code=data.code).first()
    if existing:
        return BaseResponse.error(msg="角色编码已存在", code="4001", http_status=400)

    role = Role(
        tenant_id=tenant_id,
        name=data.name,
        code=data.code,
        description=data.description,
        status=data.status,
        sort=data.sort,
    )
    await role.save()

    if data.permission_ids:
        await rbac_service.assign_permissions(role, data.permission_ids)

    return BaseResponse(data=await role.to_dict())


@router.put("/{role_id}", response_model=BaseResponse[RoleResponse])
async def update_role(
    role_id: int,
    data: RoleUpdate,
    tenant_id: int = Depends(get_current_tenant_id),
):
    """更新角色"""
    role = await Role.filter(id=role_id).first()
    if not role:
        return BaseResponse.error(msg="角色不存在", code="4004", http_status=404)

    if role.tenant_id is not None and role.tenant_id != tenant_id:
        return BaseResponse.error(msg="无权访问", code="4003", http_status=403)

    if role.is_system:
        return BaseResponse.error(msg="系统角色不能修改", code="4003", http_status=403)

    if data.name is not None:
        role.name = data.name
    if data.description is not None:
        role.description = data.description
    if data.status is not None:
        role.status = data.status
    if data.sort is not None:
        role.sort = data.sort

    await role.save()

    if data.permission_ids is not None:
        await rbac_service.assign_permissions(role, data.permission_ids)

    return BaseResponse(data=await role.to_dict())


@router.delete("/{role_id}", response_model=BaseResponse)
async def delete_role(role_id: int, tenant_id: int = Depends(get_current_tenant_id)):
    """删除角色"""
    role = await Role.filter(id=role_id).first()
    if not role:
        return BaseResponse.error(msg="角色不存在", code="4004", http_status=404)

    if role.tenant_id is not None and role.tenant_id != tenant_id:
        return BaseResponse.error(msg="无权访问", code="4003", http_status=403)

    if role.is_system:
        return BaseResponse.error(msg="系统角色不能删除", code="4003", http_status=403)

    await role.delete()
    return BaseResponse(msg="删除成功")
