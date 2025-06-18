# users/views.py
import requests
import logging

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import api_view, permission_classes, action
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
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend


User = get_user_model()
logger = logging.getLogger(__name__)

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
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'is_staff', 'is_superuser']

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

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search users in database only"""
        query = request.query_params.get('q', '').strip()
        limit = int(request.query_params.get('limit', 10))
        
        if not query:
            return Response([], status=status.HTTP_200_OK)
        
        if len(query) < 2:
            return Response(
                {'error': 'Query must be at least 2 characters long'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            users = User.objects.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(username__icontains=query) |
                Q(email__icontains=query)
            ).select_related().prefetch_related(
                'rbac_user_roles__role'
            )[:limit]
            
            serializer = UserDetailSerializer(users, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Database user search error: {str(e)}")
            return Response(
                {'error': 'Search failed'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def search_azure(self, request):
        """Search users in Azure AD only"""
        query = request.query_params.get('q', '').strip()
        limit = int(request.query_params.get('limit', 10))
        
        if not query:
            return Response({'users': [], 'has_more': False}, status=status.HTTP_200_OK)
        
        if len(query) < 2:
            return Response(
                {'error': 'Query must be at least 2 characters long'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            azure_users = search_azure_users(request.user.access_token, query, limit)
            return Response({
                'users': azure_users,
                'has_more': len(azure_users) == limit
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Azure user search error: {str(e)}")
            return Response(
                {'error': f'Azure search failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def search_combined(self, request):
        """Combined search: database + Azure with existence check"""
        query = request.query_params.get('q', '').strip()
        source = request.query_params.get('source', 'both')
        limit = int(request.query_params.get('limit', 10))
        
        if not query:
            return Response({
                'database_users': [],
                'azure_users': [],
                'azure_users_in_db': []
            }, status=status.HTTP_200_OK)
        
        if len(query) < 2:
            return Response(
                {'error': 'Query must be at least 2 characters long'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            database_users = []
            azure_users = []
            azure_users_in_db = []
            
            # Search database if requested
            if source in ['both', 'database']:
                db_users = User.objects.filter(
                    Q(first_name__icontains=query) |
                    Q(last_name__icontains=query) |
                    Q(username__icontains=query) |
                    Q(email__icontains=query)
                ).select_related().prefetch_related('rbac_user_roles__role')[:limit]
                
                serializer = UserDetailSerializer(db_users, many=True)
                database_users = serializer.data
            
            # Search Azure if requested
            if source in ['both', 'azure']:
                azure_users = search_azure_users(request.user.access_token, query, limit)
                
                # Check which Azure users exist in database
                azure_ids = [user['id'] for user in azure_users]
                existing_azure_ids = User.objects.filter(
                    azure_id__in=azure_ids
                ).values_list('azure_id', flat=True)
                azure_users_in_db = list(existing_azure_ids)
            
            return Response({
                'database_users': database_users,
                'azure_users': azure_users,
                'azure_users_in_db': azure_users_in_db
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Combined user search error: {str(e)}")
            return Response(
                {'error': f'Search failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='check_azure_user/(?P<azure_id>[^/.]+)')
    def check_azure_user(self, request, azure_id=None):
        """Check if Azure user exists in database"""
        try:
            user = User.objects.get(azure_id=azure_id)
            serializer = UserDetailSerializer(user)
            return Response({
                'exists': True,
                'user': serializer.data
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({
                'exists': False
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error checking Azure user existence: {str(e)}")
            return Response(
                {'error': 'Check failed'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def create_from_azure(self, request):
        """Create user from Azure AD info"""
        azure_user_data = request.data.get('azure_user')
        assign_default_role = request.data.get('assign_default_role', True)
        
        if not azure_user_data:
            return Response(
                {'error': 'Azure user data is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Check if user already exists
            azure_id = azure_user_data.get('id')
            if User.objects.filter(azure_id=azure_id).exists():
                return Response(
                    {'error': 'User already exists in database'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create user from Azure data
            user = create_user_from_azure_data(azure_user_data, assign_default_role)
            
            serializer = UserDetailSerializer(user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating user from Azure: {str(e)}")
            return Response(
                {'error': f'User creation failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def bulk_import_azure(self, request):
        """Bulk import Azure users to database"""
        azure_users = request.data.get('azure_users', [])
        assign_default_role = request.data.get('assign_default_role', True)
        
        if not azure_users:
            return Response(
                {'error': 'Azure users data is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []
        created_users = []
        
        for azure_user_data in azure_users:
            try:
                azure_id = azure_user_data.get('id')
                if not azure_id:
                    errors.append(f"Missing Azure ID for user: {azure_user_data}")
                    continue
                
                # Check if user exists
                try:
                    existing_user = User.objects.get(azure_id=azure_id)
                    # Update existing user
                    update_user_from_azure_data(existing_user, azure_user_data)
                    updated_count += 1
                    created_users.append(existing_user)
                    
                except User.DoesNotExist:
                    # Create new user
                    new_user = create_user_from_azure_data(azure_user_data, assign_default_role)
                    created_count += 1
                    created_users.append(new_user)
                    
            except Exception as e:
                errors.append(f"Error processing user {azure_user_data.get('displayName', 'Unknown')}: {str(e)}")
                skipped_count += 1
        
        serializer = UserDetailSerializer(created_users, many=True)
        
        return Response({
            'created_count': created_count,
            'updated_count': updated_count,
            'skipped_count': skipped_count,
            'errors': errors,
            'users': serializer.data
        }, status=status.HTTP_200_OK)

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
    

def search_azure_users(access_token, query, limit=10):
    """Search users in Azure AD using Microsoft Graph API"""
    if not access_token:
        raise Exception("Access token is required for Azure search")
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Use Microsoft Graph search API
    search_url = f"{settings.GRAPH_API_ENDPOINT}/users"
    params = {
        '$search': f'"displayName:{query}" OR "mail:{query}" OR "userPrincipalName:{query}"',
        '$select': 'id,displayName,mail,userPrincipalName,givenName,surname,jobTitle,department,officeLocation,businessPhones,mobilePhone',
        '$top': limit,
        '$count': 'true'
    }
    
    # Add ConsistencyLevel header for search
    headers['ConsistencyLevel'] = 'eventual'
    
    try:
        response = requests.get(search_url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        return data.get('value', [])
        
    except requests.RequestException as e:
        logger.error(f"Azure search request failed: {str(e)}")
        raise Exception(f"Azure search failed: {str(e)}")


def create_user_from_azure_data(azure_user_data, assign_default_role=True):
    """Create a new user from Azure AD data"""
    try:
        # Extract user information
        azure_id = azure_user_data.get('id')
        email = azure_user_data.get('mail') or azure_user_data.get('userPrincipalName')
        given_name = azure_user_data.get('givenName', '')
        surname = azure_user_data.get('surname', '')
        display_name = azure_user_data.get('displayName', '')
        
        if not azure_id or not email:
            raise Exception('Azure ID and email are required')
        
        # Generate username from email
        username = email.split('@')[0]
        
        # Ensure username is unique
        counter = 1
        original_username = username
        while User.objects.filter(username=username).exists():
            username = f"{original_username}_{counter}"
            counter += 1
        
        # Create user
        user = User.objects.create(
            username=username,
            email=email,
            first_name=given_name,
            last_name=surname,
            azure_id=azure_id,
            is_active=True
            # No password set for Azure users
        )
        
        logger.info(f"Created new user from Azure: {user.username}")
        
        # Assign default role if requested
        if assign_default_role:
            try:
                from permissions.utils import assign_role_to_user
                assign_role_to_user(user, 'Employee')
                logger.info(f"Assigned default role 'Employee' to user: {user.username}")
            except Exception as role_error:
                logger.warning(f"Failed to assign default role to user {user.username}: {str(role_error)}")
        
        return user
        
    except Exception as e:
        logger.error(f"Error creating user from Azure data: {str(e)}")
        raise


def update_user_from_azure_data(user, azure_user_data):
    """Update existing user with Azure AD data"""
    try:
        # Update user information
        email = azure_user_data.get('mail') or azure_user_data.get('userPrincipalName')
        given_name = azure_user_data.get('givenName', '')
        surname = azure_user_data.get('surname', '')
        
        if email:
            user.email = email
        if given_name:
            user.first_name = given_name
        if surname:
            user.last_name = surname
            
        user.save()
        logger.info(f"Updated user from Azure: {user.username}")
        
        return user
        
    except Exception as e:
        logger.error(f"Error updating user from Azure data: {str(e)}")
        raise