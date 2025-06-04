# permissions/serializers.py
from rest_framework import serializers
from .models import Permission, Role, UserRole, UserPermission

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'name', 'description', 'module', 'action', 'is_service']
        read_only_fields = ['is_service']

class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'permissions', 'permission_count', 'is_service', 'is_active']
        read_only_fields = ['is_service']
    
    def get_permission_count(self, obj):
        return obj.permissions.count()

class UserRoleSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)
    role_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = UserRole
        fields = ['id', 'role', 'role_id', 'is_active', 'assigned_at', 'expires_at']
        read_only_fields = ['assigned_at']

class UserPermissionSerializer(serializers.ModelSerializer):
    permission = PermissionSerializer(read_only=True)
    permission_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = UserPermission
        fields = ['id', 'permission', 'permission_id', 'granted', 'granted_at', 'expires_at']
        read_only_fields = ['granted_at']
