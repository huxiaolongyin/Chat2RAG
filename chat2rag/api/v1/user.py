from fastapi import APIRouter, Depends

from chat2rag.core.deps import get_current_user, get_current_tenant_id
from chat2rag.core.security import get_password_hash
from chat2rag.models import User
from chat2rag.schemas.base import BaseResponse, PaginatedResponse, PaginationParams
from chat2rag.schemas.user import (
    UserCreate,
    UserResponse,
    UserUpdate,
    UserDetailResponse,
)
from chat2rag.services.rbac_service import rbac_service

router = APIRouter()


@router.get("", response_model=PaginatedResponse[UserResponse])
async def get_users(
    pagination: PaginationParams = Depends(),
    tenant_id: int = Depends(get_current_tenant_id),
):
    """获取用户列表"""
    total = await User.filter(tenant_id=tenant_id).count()
    users = (
        await User.filter(tenant_id=tenant_id)
        .offset(pagination.offset)
        .limit(pagination.limit)
        .all()
    )
    return PaginatedResponse.create(
        items=[await u.to_dict() for u in users],
        total=total,
        current=pagination.current,
        size=pagination.size,
    )


@router.get("/{user_id}", response_model=BaseResponse[UserDetailResponse])
async def get_user(user_id: int, tenant_id: int = Depends(get_current_tenant_id)):
    """获取用户详情"""
    user = await User.filter(id=user_id, tenant_id=tenant_id).first()
    if not user:
        return BaseResponse.error(msg="用户不存在", code="4004", http_status=404)

    roles = await rbac_service.get_user_roles(user)
    role_codes = [r.code for r in roles]
    role_names = [r.name for r in roles]

    user_dict = await user.to_dict()
    user_dict["roles"] = role_codes
    user_dict["role_names"] = role_names

    return BaseResponse(data=user_dict)


@router.post("", response_model=BaseResponse[UserResponse])
async def create_user(
    data: UserCreate,
    tenant_id: int = Depends(get_current_tenant_id),
):
    """创建用户"""
    existing = await User.filter(tenant_id=tenant_id, username=data.username).first()
    if existing:
        return BaseResponse.error(msg="用户名已存在", code="4001", http_status=400)

    user = User(
        tenant_id=tenant_id,
        username=data.username,
        password=get_password_hash(data.password),
        phone=data.phone,
        nickname=data.nickname,
        avatar=data.avatar,
        email=data.email,
        status=data.status,
    )
    await user.save()

    if data.role_ids:
        await rbac_service.assign_roles(user, data.role_ids)

    return BaseResponse(data=await user.to_dict())


@router.put("/{user_id}", response_model=BaseResponse[UserResponse])
async def update_user(
    user_id: int,
    data: UserUpdate,
    tenant_id: int = Depends(get_current_tenant_id),
):
    """更新用户"""
    user = await User.filter(id=user_id, tenant_id=tenant_id).first()
    if not user:
        return BaseResponse.error(msg="用户不存在", code="4004", http_status=404)

    if data.phone is not None:
        user.phone = data.phone
    if data.nickname is not None:
        user.nickname = data.nickname
    if data.avatar is not None:
        user.avatar = data.avatar
    if data.email is not None:
        user.email = data.email
    if data.status is not None:
        user.status = data.status

    await user.save()

    if data.role_ids is not None:
        await rbac_service.assign_roles(user, data.role_ids)

    return BaseResponse(data=await user.to_dict())


@router.delete("/{user_id}", response_model=BaseResponse)
async def delete_user(user_id: int, tenant_id: int = Depends(get_current_tenant_id)):
    """删除用户"""
    user = await User.filter(id=user_id, tenant_id=tenant_id).first()
    if not user:
        return BaseResponse.error(msg="用户不存在", code="4004", http_status=404)

    if user.is_superuser:
        return BaseResponse.error(
            msg="不能删除超级管理员", code="4003", http_status=403
        )

    await user.delete()
    return BaseResponse(msg="删除成功")
