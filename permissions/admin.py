# permissions/admin.py
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from .models import Permission, Role, RolePermission, UserRole, UserPermission

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['name', 'module', 'action', 'is_service', 'created_at']
    list_filter = ['module', 'is_service', 'created_at']
    search_fields = ['name', 'description', 'module', 'action']
    readonly_fields = ['created_at', 'updated_at']
    
    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_service:
            return False
        return super().has_delete_permission(request, obj)
    
    def has_change_permission(self, request, obj=None):
        if obj and obj.is_service:
            return request.user.has_permission('system:manage_service_roles')
        return super().has_change_permission(request, obj)

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_service', 'is_active', 'created_at']
    list_filter = ['is_service', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['permissions']
    
    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_service:
            return False
        return super().has_delete_permission(request, obj)
    
    def has_change_permission(self, request, obj=None):
        if obj and obj.is_service:
            return request.user.has_permission('system:manage_service_roles')
        return super().has_change_permission(request, obj)

@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'is_active', 'assigned_at', 'expires_at']
    list_filter = ['is_active', 'role', 'assigned_at']
    search_fields = ['user__username', 'user__email', 'role__name']
    readonly_fields = ['assigned_at']

@admin.register(UserPermission)
class UserPermissionAdmin(admin.ModelAdmin):
    list_display = ['user', 'permission', 'granted', 'granted_at', 'expires_at']
    list_filter = ['granted', 'permission__module', 'granted_at']
    search_fields = ['user__username', 'user__email', 'permission__name']
    readonly_fields = ['granted_at']
