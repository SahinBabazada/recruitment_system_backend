# permissions/mixins.py
from django.utils import timezone
from django.db import models
from .models import Permission  # Import the Permission model

class PermissionMixin:
    """
    Mixin to add permission checking methods to User model
    """
    
    def get_all_permissions(self):
        """Get all permissions for user (from roles + direct permissions)"""
        now = timezone.now()
        
        # Get permissions from active roles
        role_permissions = Permission.objects.filter(
            roles__rbac_user_roles__user=self,
            roles__rbac_user_roles__is_active=True,
            roles__is_active=True
        ).filter(
            models.Q(roles__rbac_user_roles__expires_at__isnull=True) | 
            models.Q(roles__rbac_user_roles__expires_at__gt=now)
        ).distinct()
        
        # Get direct permissions (granted only)
        direct_permissions = Permission.objects.filter(
            rbac_user_permissions__user=self,
            rbac_user_permissions__granted=True
        ).filter(
            models.Q(rbac_user_permissions__expires_at__isnull=True) |
            models.Q(rbac_user_permissions__expires_at__gt=now)
        ).distinct()
        
        # Get denied permissions
        denied_permissions = Permission.objects.filter(
            rbac_user_permissions__user=self,
            rbac_user_permissions__granted=False
        ).filter(
            models.Q(rbac_user_permissions__expires_at__isnull=True) |
            models.Q(rbac_user_permissions__expires_at__gt=now)
        ).values_list('name', flat=True)
        
        # Combine and filter out denied permissions
        all_permissions = (role_permissions | direct_permissions).exclude(
            name__in=denied_permissions
        )
        
        return all_permissions

    def has_permission(self, permission_name):
        """Check if user has a specific permission"""
        return self.get_all_permissions().filter(name=permission_name).exists()

    def has_any_permission(self, permission_names):
        """Check if user has any of the specified permissions"""
        return self.get_all_permissions().filter(name__in=permission_names).exists()

    def has_all_permissions(self, permission_names):
        """Check if user has all of the specified permissions"""
        rbac_user_permissions = set(self.get_all_permissions().values_list('name', flat=True))
        return set(permission_names).issubset(rbac_user_permissions)

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
        now = timezone.now()
        return Role.objects.filter(
            rbac_user_roles__user=self,
            rbac_user_roles__is_active=True,
            is_active=True
        ).filter(
            models.Q(rbac_user_roles__expires_at__isnull=True) |
            models.Q(rbac_user_roles__expires_at__gt=now)
        ).distinct()