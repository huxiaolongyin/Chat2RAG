from typing import List, Optional

from chat2rag.models import Permission, Role, RolePermission, User, UserRole


class RbacService:
    """RBAC权限服务"""

    async def get_user_permissions(self, user: User) -> List[str]:
        """获取用户所有权限编码"""
        if user.is_superuser:
            return ["*"]

        permissions = set()
        user_roles = await UserRole.filter(user_id=user.id).all()

        for ur in user_roles:
            role = await Role.filter(id=ur.role_id, status=1).first()
            if not role:
                continue

            role_permissions = await RolePermission.filter(role_id=role.id).all()
            for rp in role_permissions:
                perm = await Permission.filter(id=rp.permission_id, status=1).first()
                if perm:
                    permissions.add(perm.code)

        return list(permissions)

    async def check_permission(self, user: User, permission_code: str) -> bool:
        """检查用户是否拥有指定权限"""
        if user.is_superuser:
            return True

        permissions = await self.get_user_permissions(user)
        if "*" in permissions:
            return True

        return permission_code in permissions

    async def check_permissions(self, user: User, permission_codes: List[str]) -> bool:
        """检查用户是否拥有所有指定权限"""
        if user.is_superuser:
            return True

        permissions = await self.get_user_permissions(user)
        if "*" in permissions:
            return True

        return all(code in permissions for code in permission_codes)

    async def check_any_permission(
        self, user: User, permission_codes: List[str]
    ) -> bool:
        """检查用户是否拥有任意一个指定权限"""
        if user.is_superuser:
            return True

        permissions = await self.get_user_permissions(user)
        if "*" in permissions:
            return True

        return any(code in permissions for code in permission_codes)

    async def get_user_roles(self, user: User) -> List[Role]:
        """获取用户所有角色"""
        user_roles = await UserRole.filter(user_id=user.id).all()
        role_ids = [ur.role_id for ur in user_roles]
        roles = await Role.filter(id__in=role_ids, status=1).all()
        return list(roles)

    async def assign_roles(self, user: User, role_ids: List[int]) -> None:
        """为用户分配角色"""
        await UserRole.filter(user_id=user.id).delete()

        if role_ids:
            user_roles = [
                UserRole(user_id=user.id, role_id=role_id) for role_id in role_ids
            ]
            await UserRole.bulk_create(user_roles)

    async def get_role_permissions(self, role: Role) -> List[Permission]:
        """获取角色所有权限"""
        role_permissions = await RolePermission.filter(role_id=role.id).all()
        permission_ids = [rp.permission_id for rp in role_permissions]
        permissions = await Permission.filter(id__in=permission_ids, status=1).all()
        return list(permissions)

    async def assign_permissions(self, role: Role, permission_ids: List[int]) -> None:
        """为角色分配权限"""
        await RolePermission.filter(role_id=role.id).delete()

        if permission_ids:
            role_permissions = [
                RolePermission(role_id=role.id, permission_id=perm_id)
                for perm_id in permission_ids
            ]
            await RolePermission.bulk_create(role_permissions)


rbac_service = RbacService()
