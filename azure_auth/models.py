# azure_auth/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class AppUser(AbstractUser):
    azure_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    access_token = models.TextField(null=True, blank=True)
    refresh_token = models.TextField(null=True, blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return self.email or self.username

    @property
    def is_azure_user(self):
        return bool(self.azure_id)
    
    @property
    def is_local_user(self):
        return not self.azure_id and self.password
        
    # Permission methods - these will be available after permissions app is set up
    def get_all_permissions(self):
        """Get all permissions for user (from roles + direct permissions)"""
        try:
            from permissions.mixins import PermissionMixin
            # Create a temporary instance with the mixin to use its methods
            class TempUser(PermissionMixin):
                pass
            temp = TempUser()
            # Copy necessary attributes
            for attr in ['id', 'user_roles', 'user_permissions']:
                if hasattr(self, attr):
                    setattr(temp, attr, getattr(self, attr))
            return temp.get_all_permissions()
        except ImportError:
            # permissions app not installed yet
            return []

    def has_permission(self, permission_name):
        """Check if user has a specific permission"""
        try:
            from permissions.mixins import PermissionMixin
            class TempUser(PermissionMixin):
                pass
            temp = TempUser()
            for attr in ['id', 'user_roles', 'user_permissions']:
                if hasattr(self, attr):
                    setattr(temp, attr, getattr(self, attr))
            return temp.has_permission(permission_name)
        except ImportError:
            return False

    def has_any_permission(self, permission_names):
        """Check if user has any of the specified permissions"""
        try:
            from permissions.mixins import PermissionMixin
            class TempUser(PermissionMixin):
                pass
            temp = TempUser()
            for attr in ['id', 'user_roles', 'user_permissions']:
                if hasattr(self, attr):
                    setattr(temp, attr, getattr(self, attr))
            return temp.has_any_permission(permission_names)
        except ImportError:
            return False

    def has_all_permissions(self, permission_names):
        """Check if user has all of the specified permissions"""
        try:
            from permissions.mixins import PermissionMixin
            class TempUser(PermissionMixin):
                pass
            temp = TempUser()
            for attr in ['id', 'user_roles', 'user_permissions']:
                if hasattr(self, attr):
                    setattr(temp, attr, getattr(self, attr))
            return temp.has_all_permissions(permission_names)
        except ImportError:
            return False

    def has_module_access(self, module_name):
        """Check if user has any permission for a specific module"""
        try:
            from permissions.mixins import PermissionMixin
            class TempUser(PermissionMixin):
                pass
            temp = TempUser()
            for attr in ['id', 'user_roles', 'user_permissions']:
                if hasattr(self, attr):
                    setattr(temp, attr, getattr(self, attr))
            return temp.has_module_access(module_name)
        except ImportError:
            return False

    def get_permissions_by_module(self):
        """Get user permissions grouped by module"""
        try:
            from permissions.mixins import PermissionMixin
            class TempUser(PermissionMixin):
                pass
            temp = TempUser()
            for attr in ['id', 'user_roles', 'user_permissions']:
                if hasattr(self, attr):
                    setattr(temp, attr, getattr(self, attr))
            return temp.get_permissions_by_module()
        except ImportError:
            return {}

    def get_active_roles(self):
        """Get user's active roles"""
        try:
            from permissions.mixins import PermissionMixin
            class TempUser(PermissionMixin):
                pass
            temp = TempUser()
            for attr in ['id', 'user_roles', 'user_permissions']:
                if hasattr(self, attr):
                    setattr(temp, attr, getattr(self, attr))
            return temp.get_active_roles()
        except ImportError:
            return []