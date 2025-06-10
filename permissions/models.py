
# permissions/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings

User = get_user_model()

class Permission(models.Model):
    """
    Represents a specific permission in the system
    """
    name = models.CharField(max_length=100, unique=True)  # e.g., 'mpr:create'
    description = models.TextField(blank=True)
    module = models.CharField(max_length=50)  # e.g., 'mpr', 'user', 'interview'
    action = models.CharField(max_length=50)  # e.g., 'create', 'view', 'edit', 'delete'
    is_service = models.BooleanField(default=False)  # System permissions that can't be modified
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'permissions'
        ordering = ['module', 'action']
        indexes = [
            models.Index(fields=['module', 'action']),
            models.Index(fields=['is_service']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Auto-generate name from module and action if not provided
        if not self.name:
            self.name = f"{self.module}:{self.action}"
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.is_service:
            raise ValidationError("Service permissions cannot be deleted")
        super().delete(*args, **kwargs)


class Role(models.Model):
    """
    Represents a role that can be assigned to users
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, through='RolePermission', blank=True)
    is_service = models.BooleanField(default=False)  # System roles that can't be modified
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'roles'
        ordering = ['name']

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        if self.is_service:
            raise ValidationError("Service roles cannot be deleted")
        super().delete(*args, **kwargs)

    def has_permission(self, permission_name):
        """Check if role has a specific permission"""
        return self.permissions.filter(name=permission_name).exists()

    def get_permissions_by_module(self):
        """Group permissions by module"""
        permissions = {}
        for perm in self.permissions.all():
            if perm.module not in permissions:
                permissions[perm.module] = []
            permissions[perm.module].append(perm.action)
        return permissions


class RolePermission(models.Model):
    """
    Through model for Role-Permission relationship with additional metadata
    """
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'role_permissions'
        unique_together = ['role', 'permission']

    def save(self, *args, **kwargs):
        # Prevent adding permissions to service roles unless user has manage_service_roles permission
        if self.role.is_service and self.granted_by:
            # We'll check this in the view layer instead to avoid circular import
            pass
        super().save(*args, **kwargs)


class UserRole(models.Model):
    """
    Assigns roles to users with metadata
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rbac_user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_roles')
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'rbac_user_roles'
        unique_together = ['user', 'role']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.role.name}"

    def save(self, *args, **kwargs):
        # Prevent assigning service roles unless user has manage_service_roles permission
        if self.role.is_service and self.assigned_by:
            # We'll check this in the view layer instead to avoid circular import
            pass
        super().save(*args, **kwargs)


class UserPermission(models.Model):
    """
    Direct permission assignments to users (overrides or additional permissions)
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rbac_user_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    granted = models.BooleanField(default=True)  # True = grant, False = deny
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='granted_permissions')
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'rbac_user_permissions'
        unique_together = ['user', 'permission']

    def __str__(self):
        action = "granted" if self.granted else "denied"
        return f"{self.user.username} - {self.permission.name} ({action})"