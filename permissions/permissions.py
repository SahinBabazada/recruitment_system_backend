# permissions/permissions.py (DRF Permission Classes)
from rest_framework import permissions

class HasPermission(permissions.BasePermission):
    """
    Custom permission class to check specific permissions
    """
    def __init__(self, permission_name):
        self.permission_name = permission_name
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.has_permission(self.permission_name)

class HasAnyPermission(permissions.BasePermission):
    """
    Custom permission class to check if user has any of the specified permissions
    """
    def __init__(self, permission_names):
        self.permission_names = permission_names
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.has_any_permission(self.permission_names)

class HasModuleAccess(permissions.BasePermission):
    """
    Custom permission class to check module access
    """
    def __init__(self, module_name):
        self.module_name = module_name
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.has_module_access(self.module_name)