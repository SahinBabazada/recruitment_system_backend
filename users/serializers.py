# users/serializers.py
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from permissions.models import Role, UserRole

User = get_user_model()

class HasUserPermission:
    """Custom permission class for user operations"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Map actions to required permissions
        action_permissions = {
            'list': 'user:view',
            'retrieve': 'user:view',
            'create': 'user:create',
            'update': 'user:edit',
            'partial_update': 'user:edit',
            'destroy': 'user:delete',
            'stats': 'user:view',
            'permission_summary': 'user:view',
            'bulk_toggle_status': 'user:edit',
            'bulk_assign_role': 'role:assign',
            'reset_password': 'user:reset_password',
        }
        
        required_permission = action_permissions.get(view.action, 'user:view')
        
        # Check if user has the required permission
        return request.user.has_permission(required_permission)

class UserListSerializer(serializers.ModelSerializer):
    """Serializer for user list view with minimal fields"""
    full_name = serializers.SerializerMethodField()
    active_roles = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'azure_id', 'is_active', 'is_staff', 'is_superuser', 
            'date_joined', 'last_login', 'active_roles'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()
    
    def get_active_roles(self, obj):
        # Get active roles for this user
        active_user_roles = UserRole.objects.filter(
            user=obj,
            is_active=True,
            role__is_active=True
        ).select_related('role')
        
        return [{'id': ur.role.id, 'name': ur.role.name} for ur in active_user_roles]

class UserDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed user view"""
    full_name = serializers.SerializerMethodField()
    is_azure_user = serializers.ReadOnlyField()
    is_local_user = serializers.ReadOnlyField()
    active_roles = serializers.SerializerMethodField()
    permission_count = serializers.SerializerMethodField()
    permissions_by_module = serializers.SerializerMethodField()
    all_permissions = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'azure_id', 'is_active', 'is_staff', 'is_superuser',
            'date_joined', 'last_login', 'is_azure_user', 'is_local_user',
            'active_roles', 'permission_count', 'permissions_by_module', 'all_permissions'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login', 'azure_id']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()
    
    def get_active_roles(self, obj):
        try:
            return [{'id': role.id, 'name': role.name, 'description': role.description} 
                   for role in obj.get_active_roles()]
        except:
            return []
    
    def get_permission_count(self, obj):
        try:
            return obj.get_all_permissions().count()
        except:
            return 0
    
    def get_permissions_by_module(self, obj):
        try:
            return obj.get_permissions_by_module()
        except:
            return {}
    
    def get_all_permissions(self, obj):
        try:
            return [perm.name for perm in obj.get_all_permissions()]
        except:
            return []

class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new users"""
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'password', 'confirm_password', 'is_active', 'is_staff', 'is_superuser'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def validate_password(self, value):
        import re
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long")
        if not re.search(r'(?=.*[a-z])(?=.*[A-Z])(?=.*\d)', value):
            raise serializers.ValidationError(
                "Password must contain at least one uppercase letter, one lowercase letter, and one number"
            )
        return value
    
    def validate_username(self, value):
        import re
        if not re.match(r'^[a-zA-Z0-9._-]+$', value):
            raise serializers.ValidationError(
                "Username can only contain letters, numbers, dots, hyphens, and underscores"
            )
        if len(value) < 3:
            raise serializers.ValidationError("Username must be at least 3 characters long")
        return value
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        
        # Assign default role if available
        try:
            from permissions.utils import assign_role_to_user
            assign_role_to_user(user, 'Employee')
        except Exception:
            pass  # If role assignment fails, continue without it
        
        return user

class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating existing users"""
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'is_active', 'is_staff', 'is_superuser'
        ]
    
    def validate_username(self, value):
        user = self.instance
        if User.objects.exclude(pk=user.pk).filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value
    
    def validate_email(self, value):
        user = self.instance
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

class UserPermissionSummarySerializer(serializers.Serializer):
    """Serializer for user permission summary"""
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    roles = serializers.ListField(child=serializers.CharField())
    permissions_by_module = serializers.DictField()
    all_permissions = serializers.ListField(child=serializers.CharField())

class UserStatsSerializer(serializers.Serializer):
    """Serializer for user statistics"""
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    inactive_users = serializers.IntegerField()
    staff_users = serializers.IntegerField()
    azure_users = serializers.IntegerField()
    local_users = serializers.IntegerField()
    recent_logins = serializers.IntegerField()

class BulkUserActionSerializer(serializers.Serializer):
    """Serializer for bulk user actions"""
    user_ids = serializers.ListField(child=serializers.IntegerField())
    is_active = serializers.BooleanField(required=False)
    role_id = serializers.IntegerField(required=False)
    
    def validate_user_ids(self, value):
        if not value:
            raise serializers.ValidationError("At least one user ID must be provided")
        return value

class PasswordResetSerializer(serializers.Serializer):
    """Serializer for password reset"""
    new_password = serializers.CharField(min_length=8)
    
    def validate_new_password(self, value):
        import re
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long")
        if not re.search(r'(?=.*[a-z])(?=.*[A-Z])(?=.*\d)', value):
            raise serializers.ValidationError(
                "Password must contain at least one uppercase letter, one lowercase letter, and one number"
            )
        return value