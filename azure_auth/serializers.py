from rest_framework import serializers
from django.contrib.auth import get_user_model
from permissions.models import Role

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    is_azure_user = serializers.BooleanField(read_only=True)
    is_local_user = serializers.BooleanField(read_only=True)
    active_roles = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'azure_id', 'is_active', 'is_staff', 'is_superuser', 
            'date_joined', 'last_login', 'is_azure_user', 'is_local_user',
            'active_roles'
        ]
        read_only_fields = ['date_joined', 'last_login', 'azure_id']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()

    def get_active_roles(self, obj):
        return obj.get_active_roles().values('id', 'name', 'description', 'is_service', 'permission_count')

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 'password', 
            'confirm_password', 'is_active', 'is_staff', 'is_superuser'
        ]

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        return data

    def validate_password(self, value):
        # Add password strength validation
        import re
        if not re.search(r'(?=.*[a-z])(?=.*[A-Z])(?=.*\d)', value):
            raise serializers.ValidationError(
                "Password must contain at least one uppercase letter, one lowercase letter, and one number"
            )
        return value

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        
        # Assign default role
        from permissions.utils import assign_role_to_user
        assign_role_to_user(user, 'Employee')
        
        return user