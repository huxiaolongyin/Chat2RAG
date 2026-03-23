from datetime import datetime
from typing import Optional

from chat2rag.core.logger import get_logger
from chat2rag.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    sms_code_manager,
    verify_password,
)
from chat2rag.models import Permission, Role, Tenant, User, UserRole
from chat2rag.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
    SmsLoginRequest,
    TokenResponse,
)

logger = get_logger(__name__)


class AuthService:
    def __init__(self):
        self.token_expire_seconds = 60 * 60 * 24

    async def login(
        self, request: LoginRequest, client_ip: str = None
    ) -> Optional[LoginResponse]:
        """用户名密码登录"""
        tenant = await self._get_tenant(request.tenant_code)
        if not tenant:
            return None

        user = await User.filter(tenant_id=tenant.id, username=request.username).first()
        if not user:
            return None

        if not verify_password(request.password, user.password):
            return None

        if user.status != 1:
            return None

        user.last_login_time = datetime.now()
        user.last_login_ip = client_ip
        await user.save()

        return await self._build_login_response(user, tenant)

    async def sms_login(
        self, request: SmsLoginRequest, client_ip: str = None
    ) -> Optional[LoginResponse]:
        """手机验证码登录"""
        tenant = await self._get_tenant(request.tenant_code)
        if not tenant:
            return None

        if not sms_code_manager.verify_code(request.phone, request.code):
            return None

        user = await User.filter(tenant_id=tenant.id, phone=request.phone).first()
        if not user:
            return None

        if user.status != 1:
            return None

        user.last_login_time = datetime.now()
        user.last_login_ip = client_ip
        await user.save()

        return await self._build_login_response(user, tenant)

    async def get_current_user(
        self, user_id: int, tenant_id: int
    ) -> Optional[CurrentUserResponse]:
        """获取当前用户信息"""
        user = await User.filter(id=user_id, tenant_id=tenant_id).first()
        if not user:
            return None

        tenant = await Tenant.filter(id=user.tenant_id).first()
        if not tenant:
            return None

        roles, permissions = await self._get_user_roles_and_permissions(user)

        return CurrentUserResponse(
            id=user.id,
            username=user.username,
            nickname=user.nickname,
            avatar=user.avatar,
            email=user.email,
            phone=user.phone,
            tenant_id=user.tenant_id,
            tenant_name=tenant.name,
            is_superuser=user.is_superuser,
            status=user.status,
            last_login_time=user.last_login_time,
            roles=roles,
            permissions=permissions,
        )

    async def _get_tenant(self, tenant_code: Optional[str]) -> Optional[Tenant]:
        """获取租户"""
        if tenant_code:
            tenant = await Tenant.filter(code=tenant_code, status=1).first()
        else:
            tenant = await Tenant.filter(status=1).first()
        return tenant

    async def _build_login_response(self, user: User, tenant: Tenant) -> LoginResponse:
        """构建登录响应"""
        roles, permissions = await self._get_user_roles_and_permissions(user)

        token_data = {
            "user_id": user.id,
            "tenant_id": user.tenant_id,
            "is_superuser": user.is_superuser,
        }
        access_token = create_access_token(token_data)

        return LoginResponse(
            token=TokenResponse(
                access_token=access_token,
                token_type="Bearer",
                expires_in=self.token_expire_seconds,
            ),
            user_id=user.id,
            username=user.username,
            nickname=user.nickname,
            avatar=user.avatar,
            tenant_id=user.tenant_id,
            tenant_name=tenant.name,
            is_superuser=user.is_superuser,
            roles=roles,
            permissions=permissions,
        )

    async def _get_user_roles_and_permissions(
        self, user: User
    ) -> tuple[list[str], list[str]]:
        """获取用户角色和权限"""
        if user.is_superuser:
            roles = ["super_admin"]
            permissions = ["*"]
            return roles, permissions

        user_roles = await UserRole.filter(user_id=user.id).prefetch_related("role")
        roles = []
        permission_set = set()

        for ur in user_roles:
            role = await ur.role
            if role and role.status == 1:
                roles.append(role.code)
                role_permissions = await role.role_permissions.all().prefetch_related(
                    "permission"
                )
                for rp in role_permissions:
                    perm = await rp.permission
                    if perm and perm.status == 1:
                        permission_set.add(perm.code)

        return roles, list(permission_set)


auth_service = AuthService()
