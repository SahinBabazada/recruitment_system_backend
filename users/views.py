# users/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from permissions.models import Role, UserRole
from .serializers import (
    UserListSerializer, 
    UserDetailSerializer, 
    UserCreateSerializer, 
    UserUpdateSerializer
)

User = get_user_model()

class HasUserPermission(permissions.BasePermission):
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

class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for managing users"""
    queryset = User.objects.all()
    permission_classes = [HasUserPermission]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return UserListSerializer
        elif self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        else:
            return UserDetailSerializer
    
    def get_queryset(self):
        """Filter queryset based on request parameters"""
        queryset = User.objects.select_related().prefetch_related(
            'rbac_user_roles__role',
            'rbac_user_roles__role__permissions'
        )
        
        # Apply filters
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(username__icontains=search) |
                Q(email__icontains=search)
            )
        
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
            
        is_staff = self.request.query_params.get('is_staff')
        if is_staff is not None:
            queryset = queryset.filter(is_staff=is_staff.lower() == 'true')
            
        is_superuser = self.request.query_params.get('is_superuser')
        if is_superuser is not None:
            queryset = queryset.filter(is_superuser=is_superuser.lower() == 'true')
            
        has_azure_id = self.request.query_params.get('has_azure_id')
        if has_azure_id is not None:
            if has_azure_id.lower() == 'true':
                queryset = queryset.exclude(azure_id__isnull=True).exclude(azure_id='')
            else:
                queryset = queryset.filter(Q(azure_id__isnull=True) | Q(azure_id=''))
        
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(rbac_user_roles__role_id=role, rbac_user_roles__is_active=True)
        
        return queryset.distinct()

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user == request.user:
            return Response(
                {'error': 'You cannot delete your own account'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        if user.is_superuser and not request.user.is_superuser:
            return Response(
                {'error': 'You cannot delete a superuser account'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get user statistics"""
        now = timezone.now()
        recent_threshold = now - timedelta(days=7)
        
        stats = {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'inactive_users': User.objects.filter(is_active=False).count(),
            'staff_users': User.objects.filter(is_staff=True).count(),
            'azure_users': User.objects.exclude(azure_id__isnull=True).exclude(azure_id='').count(),
            'local_users': User.objects.filter(Q(azure_id__isnull=True) | Q(azure_id='')).count(),
            'recent_logins': User.objects.filter(last_login__gte=recent_threshold).count(),
        }
        return Response(stats)

    @action(detail=True, methods=['get'])
    def permission_summary(self, request, pk=None):
        """Get user permission summary"""
        user = self.get_object()
        try:
            from permissions.utils import get_rbac_user_permissions_summary
            summary = get_rbac_user_permissions_summary(user)
            return Response(summary)
        except Exception as e:
            # Fallback if utility function doesn't exist
            return Response({
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'roles': [role.name for role in user.get_active_roles()],
                'permissions_by_module': user.get_permissions_by_module(),
                'all_permissions': [perm.name for perm in user.get_all_permissions()],
            })

    @action(detail=False, methods=['post'])
    def bulk_toggle_status(self, request):
        """Bulk activate/deactivate users"""
        user_ids = request.data.get('user_ids', [])
        is_active = request.data.get('is_active', True)
        
        if not user_ids:
            return Response(
                {'error': 'No user IDs provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Prevent deactivating current user
        if not is_active and request.user.id in user_ids:
            return Response(
                {'error': 'You cannot deactivate your own account'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        updated_count = User.objects.filter(id__in=user_ids).update(is_active=is_active)
        
        return Response({
            'updated_count': updated_count,
            'message': f'Successfully {"activated" if is_active else "deactivated"} {updated_count} users'
        })

    @action(detail=False, methods=['post'])
    def bulk_assign_role(self, request):
        """Bulk assign role to users"""
        user_ids = request.data.get('user_ids', [])
        role_id = request.data.get('role_id')
        
        if not user_ids or not role_id:
            return Response(
                {'error': 'User IDs and role ID are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            role = Role.objects.get(id=role_id)
            assigned_count = 0
            
            for user_id in user_ids:
                try:
                    user_role, created = UserRole.objects.get_or_create(
                        user_id=user_id,
                        role=role,
                        defaults={'assigned_by': request.user}
                    )
                    if created:
                        assigned_count += 1
                except Exception:
                    continue  # Skip if user doesn't exist or other error
            
            return Response({
                'assigned_count': assigned_count,
                'message': f'Successfully assigned role to {assigned_count} users'
            })
        except Role.DoesNotExist:
            return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """Reset user password (for local users only)"""
        user = self.get_object()
        new_password = request.data.get('new_password')
        
        if not new_password:
            return Response(
                {'error': 'New password is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if user.azure_id:
            return Response(
                {'error': 'Cannot reset password for Azure SSO users'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate password strength
        import re
        if len(new_password) < 8:
            return Response(
                {'error': 'Password must be at least 8 characters long'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        if not re.search(r'(?=.*[a-z])(?=.*[A-Z])(?=.*\d)', new_password):
            return Response(
                {'error': 'Password must contain at least one uppercase letter, one lowercase letter, and one number'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(new_password)
        user.save()
        
        return Response({'message': 'Password reset successfully'})