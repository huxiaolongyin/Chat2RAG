from typing import List

from fastapi import APIRouter, Depends

from chat2rag.core.deps import (
    get_current_user,
    get_current_tenant_id,
    require_permissions,
)
from chat2rag.models import Permission
from chat2rag.schemas.base import BaseResponse, PaginatedResponse, PaginationParams
from chat2rag.schemas.permission import (
    PermissionCreate,
    PermissionResponse,
    PermissionTreeResponse,
    PermissionUpdate,
)

router = APIRouter()


@router.get("", response_model=PaginatedResponse[PermissionResponse])
async def get_permissions(pagination: PaginationParams = Depends()):
    """获取权限列表"""
    total = await Permission.all().count()
    permissions = (
        await Permission.all()
        .offset(pagination.offset)
        .limit(pagination.limit)
        .order_by("sort")
    )
    return PaginatedResponse.create(
        items=[await p.to_dict() for p in permissions],
        total=total,
        current=pagination.current,
        size=pagination.size,
    )


@router.get("/tree", response_model=BaseResponse[List[PermissionTreeResponse]])
async def get_permission_tree():
    """获取权限树"""
    permissions = await Permission.all().order_by("sort")
    permission_map = {p.id: p for p in permissions}

    tree: List[PermissionTreeResponse] = []

    for perm in permissions:
        if perm.parent_id is None:
            tree.append(await build_permission_tree(perm, permission_map))

    return BaseResponse(data=tree)


async def build_permission_tree(perm: Permission, permission_map: dict) -> dict:
    """构建权限树"""
    perm_dict = await perm.to_dict()
    perm_dict["children"] = []

    for child_id, child in permission_map.items():
        if child.parent_id == perm.id:
            perm_dict["children"].append(
                await build_permission_tree(child, permission_map)
            )

    return perm_dict


@router.post("", response_model=BaseResponse[PermissionResponse])
async def create_permission(data: PermissionCreate):
    """创建权限"""
    existing = await Permission.filter(code=data.code).first()
    if existing:
        return BaseResponse.error(msg="权限编码已存在", code="4001", http_status=400)

    permission = Permission(
        parent_id=data.parent_id,
        name=data.name,
        code=data.code,
        type=data.type,
        path=data.path,
        component=data.component,
        icon=data.icon,
        sort=data.sort,
        status=data.status,
        visible=data.visible,
        cache=data.cache,
        remark=data.remark,
    )
    await permission.save()
    return BaseResponse(data=await permission.to_dict())


@router.put("/{permission_id}", response_model=BaseResponse[PermissionResponse])
async def update_permission(permission_id: int, data: PermissionUpdate):
    """更新权限"""
    permission = await Permission.filter(id=permission_id).first()
    if not permission:
        return BaseResponse.error(msg="权限不存在", code="4004", http_status=404)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(permission, field, value)

    await permission.save()
    return BaseResponse(data=await permission.to_dict())


@router.delete("/{permission_id}", response_model=BaseResponse)
async def delete_permission(permission_id: int):
    """删除权限"""
    permission = await Permission.filter(id=permission_id).first()
    if not permission:
        return BaseResponse.error(msg="权限不存在", code="4004", http_status=404)

    children = await Permission.filter(parent_id=permission_id).count()
    if children > 0:
        return BaseResponse.error(
            msg="存在子权限，不能删除", code="4003", http_status=403
        )

    await permission.delete()
    return BaseResponse(msg="删除成功")
