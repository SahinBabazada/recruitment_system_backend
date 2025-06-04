# permissions/mixins.py
from django.utils import timezone
from django.db import models

class PermissionMixin:
    """
    Mixin to add permission checking methods to User model
    """
    
    def get_all_permissions(self):
        """Get all permissions for user (from roles + direct permissions)"""
        from .models import Permission, UserRole, UserPermission
        
        now = timezone.now()
        
        # Step 1: Get user's active roles
        active_user_roles = UserRole.objects.filter(
            user=self,
            is_active=True,
            role__is_active=True
        ).filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now)
        )
        
        # Step 2: Get role IDs
        active_role_ids = list(active_user_roles.values_list('role_id', flat=True))
        
        # Step 3: Get permissions from those roles
        if active_role_ids:
            role_permissions = Permission.objects.filter(
                rolepermission__role_id__in=active_role_ids
            ).distinct()
        else:
            role_permissions = Permission.objects.none()
        
        # Step 4: Get direct permissions (granted only)
        direct_permissions = Permission.objects.filter(
            userpermission__user=self,
            userpermission__granted=True
        ).filter(
            models.Q(userpermission__expires_at__isnull=True) |
            models.Q(userpermission__expires_at__gt=now)
        ).distinct()
        
        # Step 5: Get denied permissions (direct denials override role permissions)
        denied_permission_names = list(UserPermission.objects.filter(
            user=self,
            granted=False
        ).filter(
            models.Q(expires_at__isnull=True) |
            models.Q(expires_at__gt=now)
        ).values_list('permission__name', flat=True))
        
        # Step 6: Combine and filter out denied permissions
        if denied_permission_names:
            all_permissions = (role_permissions | direct_permissions).exclude(
                name__in=denied_permission_names
            ).distinct()
        else:
            all_permissions = (role_permissions | direct_permissions).distinct()
        
        return all_permissions

    def has_permission(self, permission_name):
        """Check if user has a specific permission"""
        return self.get_all_permissions().filter(name=permission_name).exists()

    def has_any_permission(self, permission_names):
        """Check if user has any of the specified permissions"""
        return self.get_all_permissions().filter(name__in=permission_names).exists()

    def has_all_permissions(self, permission_names):
        """Check if user has all of the specified permissions"""
        user_permissions = set(self.get_all_permissions().values_list('name', flat=True))
        return set(permission_names).issubset(user_permissions)

    def has_module_access(self, module_name):
        """Check if user has any permission for a specific module"""
        return self.get_all_permissions().filter(module=module_name).exists()

    def get_permissions_by_module(self):
        """Get user permissions grouped by module"""
        permissions = {}
        for perm in self.get_all_permissions():
            if perm.module not in permissions:
                permissions[perm.module] = []
            permissions[perm.module].append(perm.action)
        return permissions

    def get_active_roles(self):
        """Get user's active roles"""
        from .models import Role, UserRole
        
        now = timezone.now()
        
        # Get active UserRole records for this user
        active_user_roles = UserRole.objects.filter(
            user=self,
            is_active=True,
            role__is_active=True
        ).filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now)
        )
        
        # Get the role IDs and then fetch the actual Role objects
        role_ids = list(active_user_roles.values_list('role_id', flat=True))
        
        if role_ids:
            return Role.objects.filter(id__in=role_ids)
        else:
            return Role.objects.none()