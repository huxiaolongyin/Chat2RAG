from typing import List, Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from chat2rag.core.security import decode_access_token
from chat2rag.models import User
from chat2rag.schemas.auth import CurrentUserResponse
from chat2rag.services.auth_service import auth_service

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> CurrentUserResponse:
    """获取当前登录用户"""
    if credentials is None:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="未登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="无效的Token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("user_id")
    tenant_id = payload.get("tenant_id")

    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="无效的Token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await auth_service.get_current_user(user_id, tenant_id)
    if user is None:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[CurrentUserResponse]:
    """获取当前登录用户（可选）"""
    if credentials is None:
        return None

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        return None

    user_id = payload.get("user_id")
    tenant_id = payload.get("tenant_id")

    if not user_id or not tenant_id:
        return None

    user = await auth_service.get_current_user(user_id, tenant_id)
    return user


async def get_current_tenant_id(
    current_user: CurrentUserResponse = Depends(get_current_user),
) -> int:
    """获取当前租户ID"""
    return current_user.tenant_id


class PermissionChecker:
    """权限检查器"""

    def __init__(self, permissions: List[str], mode: str = "all"):
        self.permissions = permissions
        self.mode = mode

    async def __call__(
        self, current_user: CurrentUserResponse = Depends(get_current_user)
    ) -> CurrentUserResponse:
        if current_user.is_superuser:
            return current_user

        if "*" in current_user.permissions:
            return current_user

        if self.mode == "all":
            has_permission = all(
                p in current_user.permissions for p in self.permissions
            )
        else:
            has_permission = any(
                p in current_user.permissions for p in self.permissions
            )

        if not has_permission:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="权限不足",
            )

        return current_user


def require_permissions(*permissions: str, mode: str = "all"):
    """权限依赖"""
    return Depends(PermissionChecker(list(permissions), mode))
