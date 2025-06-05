# permissions/admin.py
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db import models
from django.forms import CheckboxSelectMultiple
from .models import Permission, Role, RolePermission, UserRole, UserPermission

class RolePermissionInline(admin.TabularInline):
    """Inline for managing role permissions"""
    model = RolePermission
    extra = 0
    autocomplete_fields = ['permission']
    readonly_fields = ['granted_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('permission', 'granted_by')

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['name', 'module', 'action', 'is_service', 'created_at']
    list_filter = ['module', 'is_service', 'created_at']
    search_fields = ['name', 'description', 'module', 'action']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 50
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'module', 'action')
        }),
        ('Settings', {
            'fields': ('is_service',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
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
    list_display = ['name', 'is_service', 'is_active', 'permission_count', 'created_at']
    list_filter = ['is_service', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 50
    inlines = [RolePermissionInline]  # Use inline instead of filter_horizontal
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
        }),
        ('Settings', {
            'fields': ('is_service', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def permission_count(self, obj):
        """Display the number of permissions for this role"""
        return obj.permissions.count()
    permission_count.short_description = 'Permissions'
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('permissions')
    
    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_service:
            return False
        return super().has_delete_permission(request, obj)
    
    def has_change_permission(self, request, obj=None):
        if obj and obj.is_service:
            return request.user.has_permission('system:manage_service_roles')
        return super().has_change_permission(request, obj)

@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    """Direct management of role-permission relationships"""
    list_display = ['role', 'permission', 'granted_by', 'granted_at']
    list_filter = ['granted_at', 'role__is_service', 'permission__module']
    search_fields = ['role__name', 'permission__name', 'permission__module']
    readonly_fields = ['granted_at']
    autocomplete_fields = ['role', 'permission', 'granted_by']
    list_per_page = 100
    
    fieldsets = (
        ('Assignment', {
            'fields': ('role', 'permission')
        }),
        ('Metadata', {
            'fields': ('granted_by', 'granted_at')
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('role', 'permission', 'granted_by')
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set granted_by for new objects
            obj.granted_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'is_active', 'assigned_at', 'expires_at', 'assigned_by']
    list_filter = ['is_active', 'role', 'assigned_at', 'expires_at']
    search_fields = ['user__username', 'user__email', 'role__name']
    readonly_fields = ['assigned_at']
    autocomplete_fields = ['user', 'role', 'assigned_by']
    list_per_page = 100
    
    fieldsets = (
        ('Assignment', {
            'fields': ('user', 'role', 'is_active')
        }),
        ('Schedule', {
            'fields': ('expires_at',)
        }),
        ('Metadata', {
            'fields': ('assigned_by', 'assigned_at')
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'role', 'assigned_by')
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set assigned_by for new objects
            obj.assigned_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(UserPermission)
class UserPermissionAdmin(admin.ModelAdmin):
    list_display = ['user', 'permission', 'granted', 'granted_at', 'expires_at', 'granted_by']
    list_filter = ['granted', 'permission__module', 'granted_at', 'expires_at']
    search_fields = ['user__username', 'user__email', 'permission__name']
    readonly_fields = ['granted_at']
    autocomplete_fields = ['user', 'permission', 'granted_by']
    list_per_page = 100
    
    fieldsets = (
        ('Assignment', {
            'fields': ('user', 'permission', 'granted')
        }),
        ('Schedule', {
            'fields': ('expires_at',)
        }),
        ('Metadata', {
            'fields': ('granted_by', 'granted_at')
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'permission', 'granted_by')
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set granted_by for new objects
            obj.granted_by = request.user
        super().save_model(request, obj, form, change)

# Enhanced search capabilities are already included in the main admin classes above

# Custom admin site configuration
admin.site.site_header = "Recruitment System Administration"
admin.site.site_title = "Recruitment Admin"
admin.site.index_title = "Welcome to Recruitment System Administration"

# Add some admin actions
@admin.action(description='Activate selected roles')
def activate_roles(modeladmin, request, queryset):
    """Bulk activate roles"""
    updated = queryset.update(is_active=True)
    modeladmin.message_user(request, f'{updated} roles were successfully activated.')

@admin.action(description='Deactivate selected roles')
def deactivate_roles(modeladmin, request, queryset):
    """Bulk deactivate roles"""
    updated = queryset.update(is_active=False)
    modeladmin.message_user(request, f'{updated} roles were successfully deactivated.')

@admin.action(description='Activate selected user roles')
def activate_user_roles(modeladmin, request, queryset):
    """Bulk activate user roles"""
    updated = queryset.update(is_active=True)
    modeladmin.message_user(request, f'{updated} user roles were successfully activated.')

@admin.action(description='Deactivate selected user roles')
def deactivate_user_roles(modeladmin, request, queryset):
    """Bulk deactivate user roles"""
    updated = queryset.update(is_active=False)
    modeladmin.message_user(request, f'{updated} user roles were successfully deactivated.')

# Add actions to admin classes
RoleAdmin.actions = [activate_roles, deactivate_roles]
UserRoleAdmin.actions = [activate_user_roles, deactivate_user_roles]