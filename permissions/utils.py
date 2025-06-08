# permissions/utils.py
from django.contrib.auth import get_user_model
from .models import Role, Permission, UserRole
from django.db import transaction

User = get_user_model()

def assign_role_to_user(user, role_name, assigned_by=None, expires_at=None):
    """
    Utility function to assign a role to a user
    """
    try:
        role = Role.objects.get(name=role_name)
        user_role, created = UserRole.objects.get_or_create(
            user=user,
            role=role,
            defaults={
                'assigned_by': assigned_by,
                'expires_at': expires_at
            }
        )
        return user_role, created
    except Role.DoesNotExist:
        raise ValueError(f"Role '{role_name}' does not exist")

def remove_role_from_user(user, role_name):
    """
    Utility function to remove a role from a user
    """
    try:
        role = Role.objects.get(name=role_name)
        UserRole.objects.filter(user=user, role=role).delete()
        return True
    except Role.DoesNotExist:
        raise ValueError(f"Role '{role_name}' does not exist")

def get_rbac_user_permissions_summary(user):
    """
    Get a comprehensive summary of user's permissions
    """
    return {
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        'roles': [role.name for role in user.get_active_roles()],
        'permissions_by_module': user.get_permissions_by_module(),
        'all_permissions': [perm.name for perm in user.get_all_permissions()],
    }

@transaction.atomic
def bulk_assign_permissions_to_role(role, permission_names, assigned_by=None):
    """
    Bulk assign permissions to a role
    """
    permissions = Permission.objects.filter(name__in=permission_names)
    found_permissions = set(permissions.values_list('name', flat=True))
    missing_permissions = set(permission_names) - found_permissions
    
    if missing_permissions:
        raise ValueError(f"Permissions not found: {list(missing_permissions)}")
    
    for permission in permissions:
        role.permissions.add(permission)
    
    return len(permissions)
