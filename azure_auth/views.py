# azure_auth/views.py

import jwt
import requests
import urllib.parse
from django.shortcuts import redirect
from django.conf import settings
from django.contrib.auth import login
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status,viewsets

from django.contrib.auth import authenticate, login as django_login
from rest_framework.authtoken.models import Token

from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from permissions.decorators import permission_required

User = get_user_model()

@api_view(['GET'])
@permission_classes([AllowAny])
def azure_login(request):
    """Redirect to Azure AD login page"""
    auth_url = f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}/oauth2/v2.0/authorize"
    
    params = {
        'client_id': settings.AZURE_AD_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': settings.AZURE_AD_REDIRECT_URI,
        'scope': 'openid profile email User.Read Mail.Read Calendars.Read Files.Read',
        'response_mode': 'query',
        'state': 'random_state_string'  # Use proper state management in production
    }
    
    auth_url_with_params = f"{auth_url}?{urllib.parse.urlencode(params)}"
    return JsonResponse({'auth_url': auth_url_with_params})

# Add these two new views
@api_view(['POST'])
@permission_classes([AllowAny])
def local_login(request):
    """Traditional username/password login"""
    from django.contrib.auth import get_user_model

    User = get_user_model()

    username_or_email = request.data.get('username')  # This field can contain username OR email
    password = request.data.get('password')
    
    if not username_or_email or not password:
        return JsonResponse({'error': 'Username/email and password required'}, status=400)
    
    # Check if it's an email (contains @)
    if '@' in username_or_email:
        # It's an email, find the user by email
        try:
            user_obj = User.objects.get(email=username_or_email)
            username = user_obj.username
        except User.DoesNotExist:
            return JsonResponse({'error': 'Invalid credentials'}, status=400)
    else:
        # It's a username
        username = username_or_email
    
    # Authenticate with username
    user = authenticate(username=username, password=password)
    
    if user:
        django_login(request, user)
        token, created = Token.objects.get_or_create(user=user)
        return JsonResponse({
            'token': token.key,
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'login_type': 'local'
        })
    
    return JsonResponse({'error': 'Invalid credentials'}, status=400)


@api_view(['POST'])
@permission_classes([AllowAny])
def local_register(request):
    """Traditional user registration"""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')
    
    if not all([username, email, password]):
        return JsonResponse({'error': 'Username, email and password required'}, status=400)
    
    if User.objects.filter(username=username).exists():
        return JsonResponse({'error': 'Username already exists'}, status=400)
        
    if User.objects.filter(email=email).exists():
        return JsonResponse({'error': 'Email already exists'}, status=400)
    
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name
    )
    
    # Assign default role
    from permissions.utils import assign_role_to_user
    assign_role_to_user(user, 'Employee')
    
    token, created = Token.objects.get_or_create(user=user)
    
    return JsonResponse({
        'message': 'User created successfully',
        'token': token.key,
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        'login_type': 'local'
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def azure_callback(request):
    """Handle Azure AD callback and redirect to frontend"""
    code = request.GET.get('code')
    error = request.GET.get('error')
    error_description = request.GET.get('error_description')
    
    # Frontend URLs
    frontend_success_url = getattr(settings, 'FRONTEND_SUCCESS_URL', 'http://localhost:3000/auth/callback')
    frontend_error_url = getattr(settings, 'FRONTEND_ERROR_URL', 'http://localhost:3000/login')
    
    if error:
        error_params = urllib.parse.urlencode({
            'error': error,
            'error_description': error_description or 'Authentication failed'
        })
        return redirect(f"{frontend_error_url}?{error_params}")
    
    if not code:
        error_params = urllib.parse.urlencode({
            'error': 'no_code',
            'error_description': 'No authorization code received'
        })
        return redirect(f"{frontend_error_url}?{error_params}")
    
    try:
        # Exchange code for tokens
        token_url = f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}/oauth2/v2.0/token"
        
        token_data = {
            'client_id': settings.AZURE_AD_CLIENT_ID,
            'client_secret': settings.AZURE_AD_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': settings.AZURE_AD_REDIRECT_URI,
            'scope': 'openid profile email User.Read Mail.Read Calendars.Read Files.Read'
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_json = token_response.json()
        
        if 'access_token' not in token_json:
            error_params = urllib.parse.urlencode({
                'error': 'token_exchange_failed',
                'error_description': f'Failed to exchange code for access token: {token_json.get("error_description", "Unknown error")}'
            })
            return redirect(f"{frontend_error_url}?{error_params}")
        
        access_token = token_json['access_token']
        id_token = token_json.get('id_token')  # This is what we need for user verification
        
        # If we have an ID token, use it for user verification, otherwise use access token
        token_to_verify = id_token if id_token else access_token
        
        # Get user info and create/update user
        try:
            # Instead of verifying JWT (which is complex), let's get user info from Microsoft Graph
            user_info = get_user_info_from_graph(access_token)
            user = create_or_update_user_from_graph(user_info, access_token)
            
            # Create success redirect with user data
            success_params = urllib.parse.urlencode({
                'token': access_token,
                'user_id': user.id,
                'email': user.email,
                'username': user.username,
                'first_name': user.first_name or '',
                'last_name': user.last_name or ''
            })
            
            return redirect(f"{frontend_success_url}?{success_params}")
            
        except Exception as e:
            error_params = urllib.parse.urlencode({
                'error': 'user_creation_failed',
                'error_description': str(e)
            })
            return redirect(f"{frontend_error_url}?{error_params}")
            
    except Exception as e:
        error_params = urllib.parse.urlencode({
            'error': 'authentication_failed',
            'error_description': str(e)
        })
        return redirect(f"{frontend_error_url}?{error_params}")

def get_user_info_from_graph(access_token):
    """Get user information from Microsoft Graph API"""
    headers = {'Authorization': f'Bearer {access_token}'}
    
    try:
        response = requests.get(
            f"{settings.GRAPH_API_ENDPOINT}/me",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f'Failed to get user info from Microsoft Graph: {str(e)}')

def create_or_update_user_from_graph(user_info, access_token):
    """Create or update user from Microsoft Graph user info"""
    from django.contrib.auth import get_user_model
    import logging
    
    User = get_user_model()
    logger = logging.getLogger(__name__)
    
    try:
        # Extract user information from Graph API response
        azure_id = user_info.get('id')  # Microsoft Graph uses 'id' not 'oid'
        email = user_info.get('mail') or user_info.get('userPrincipalName')
        given_name = user_info.get('givenName', '')
        surname = user_info.get('surname', '')
        display_name = user_info.get('displayName', '')
        
        logger.info(f"Creating/updating user - Azure ID: {azure_id}, Email: {email}")
        
        if not azure_id:
            raise Exception('Azure user ID not found in Graph response')
        
        if not email:
            raise Exception('Email not found in Graph response')
        
        try:
            # Try to find existing user by Azure ID
            user = User.objects.get(azure_id=azure_id)
            # Update access token and other info
            user.access_token = access_token
            user.email = email
            if given_name:
                user.first_name = given_name
            if surname:
                user.last_name = surname
            user.save()
            logger.info(f"Updated existing user: {user.username}")
            
        except User.DoesNotExist:
            # Create new user
            username = email.split('@')[0]  # Use email prefix as username
            
            # Ensure username is unique
            counter = 1
            original_username = username
            while User.objects.filter(username=username).exists():
                username = f"{original_username}_{counter}"
                counter += 1
            
            user = User.objects.create(
                username=username,
                email=email,
                first_name=given_name,
                last_name=surname,
                azure_id=azure_id,
                access_token=access_token
            )
            logger.info(f"Created new user: {user.username}")
            
            # Assign default role to new users
            try:
                from permissions.utils import assign_role_to_user
                assign_role_to_user(user, 'Employee')  # or 'HR Specialist' depending on your needs
                logger.info(f"Assigned default role 'Employee' to user: {user.username}")
            except Exception as role_error:
                logger.warning(f"Failed to assign default role to user {user.username}: {str(role_error)}")
        
        return user
        
    except Exception as e:
        logger.error(f"Error creating/updating user: {str(e)}")
        raise Exception(f'User creation failed: {str(e)}')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """Get current user's profile from Microsoft Graph"""
    headers = {'Authorization': f'Bearer {request.user.access_token}'}
    
    try:
        response = requests.get(
            f"{settings.GRAPH_API_ENDPOINT}/me",
            headers=headers
        )
        response.raise_for_status()
        return JsonResponse(response.json())
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_emails(request):
    """Get user's emails from Microsoft Graph"""
    headers = {'Authorization': f'Bearer {request.user.access_token}'}
    
    try:
        response = requests.get(
            f"{settings.GRAPH_API_ENDPOINT}/me/messages",
            headers=headers,
            params={'$top': 10, '$select': 'subject,from,receivedDateTime,isRead'}
        )
        response.raise_for_status()
        return JsonResponse(response.json())
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_calendar(request):
    """Get user's calendar events from Microsoft Graph"""
    headers = {'Authorization': f'Bearer {request.user.access_token}'}
    
    try:
        response = requests.get(
            f"{settings.GRAPH_API_ENDPOINT}/me/events",
            headers=headers,
            params={'$top': 10, '$select': 'subject,start,end,organizer'}
        )
        response.raise_for_status()
        return JsonResponse(response.json())
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_files(request):
    """Get user's OneDrive files from Microsoft Graph"""
    headers = {'Authorization': f'Bearer {request.user.access_token}'}
    
    try:
        response = requests.get(
            f"{settings.GRAPH_API_ENDPOINT}/me/drive/root/children",
            headers=headers,
            params={'$select': 'name,size,createdDateTime,lastModifiedDateTime'}
        )
        response.raise_for_status()
        return JsonResponse(response.json())
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def azure_logout(request):
    """Handle Azure AD logout and clear user session"""
    # Clear Django session
    if hasattr(request, 'user') and request.user.is_authenticated:
        # Clear stored tokens
        request.user.access_token = None
        request.user.refresh_token = None
        request.user.save()
    
    # Logout from Django session
    from django.contrib.auth import logout
    logout(request)
    
    # Return success response
    return JsonResponse({
        'message': 'Logged out successfully',
        'azure_logout_url': f'https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}/oauth2/v2.0/logout'
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def refresh_token(request):
    """Refresh the access token using refresh token"""
    if not request.user.refresh_token:
        return JsonResponse({'error': 'No refresh token available'}, status=400)
    
    token_url = f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}/oauth2/v2.0/token"
    
    token_data = {
        'client_id': settings.AZURE_AD_CLIENT_ID,
        'client_secret': settings.AZURE_AD_CLIENT_SECRET,
        'refresh_token': request.user.refresh_token,
        'grant_type': 'refresh_token',
        'scope': 'openid profile email User.Read Mail.Read Calendars.Read Files.Read'
    }
    
    response = requests.post(token_url, data=token_data)
    token_json = response.json()
    
    if 'access_token' in token_json:
        request.user.access_token = token_json['access_token']
        if 'refresh_token' in token_json:
            request.user.refresh_token = token_json['refresh_token']
        request.user.save()
        
        return JsonResponse({'message': 'Token refreshed successfully'})
    
    return JsonResponse({'error': 'Failed to refresh token'}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_dashboard_data(request):
    """Get multiple user data in one request using Graph batch API"""
    headers = {
        'Authorization': f'Bearer {request.user.access_token}',
        'Content-Type': 'application/json'
    }
    
    batch_request = {
        "requests": [
            {
                "id": "1",
                "method": "GET",
                "url": "/me"
            },
            {
                "id": "2", 
                "method": "GET",
                "url": "/me/messages?$top=5&$select=subject,from,receivedDateTime"
            },
            {
                "id": "3",
                "method": "GET", 
                "url": "/me/events?$top=5&$select=subject,start,end"
            }
        ]
    }
    
    try:
        response = requests.post(
            f"{settings.GRAPH_API_ENDPOINT}/$batch",
            headers=headers,
            json=batch_request
        )
        response.raise_for_status()
        return JsonResponse(response.json())
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['GET'])
@permission_classes([AllowAny])
def debug_auth(request):
    """Debug endpoint to test auth setup - REMOVE IN PRODUCTION"""
    auth_header = request.META.get('HTTP_AUTHORIZATION', 'None')
    
    debug_info = {
        'message': 'Auth debug endpoint',
        'auth_header_present': auth_header != 'None',
        'auth_header_format': auth_header[:20] + '...' if len(auth_header) > 20 else auth_header,
        'settings': {
            'client_id_set': bool(getattr(settings, 'AZURE_AD_CLIENT_ID', None)),
            'graph_endpoint': getattr(settings, 'GRAPH_API_ENDPOINT', 'Not set'),
            'cors_origins': getattr(settings, 'CORS_ALLOWED_ORIGINS', []),
        }
    }
    
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        try:
            # Test token with Microsoft Graph
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(
                f"{settings.GRAPH_API_ENDPOINT}/me",
                headers=headers,
                timeout=5
            )
            debug_info['graph_api_test'] = {
                'status_code': response.status_code,
                'success': response.status_code == 200,
                'response_size': len(response.content) if response.content else 0
            }
            
            if response.status_code == 200:
                user_data = response.json()
                debug_info['user_info'] = {
                    'id': user_data.get('id'),
                    'email': user_data.get('mail') or user_data.get('userPrincipalName'),
                    'display_name': user_data.get('displayName')
                }
        except Exception as e:
            debug_info['graph_api_test'] = {
                'error': str(e)
            }
    
    return JsonResponse(debug_info, indent=2)
    
@api_view(['GET'])
@permission_classes([AllowAny])
def debug_token(request):
    """Debug view to inspect tokens - REMOVE IN PRODUCTION"""
    code = request.GET.get('code')
    
    if not code:
        return JsonResponse({'error': 'No code provided'})
    
    try:
        # Exchange code for tokens (same as in azure_callback)
        token_url = f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}/oauth2/v2.0/token"
        
        token_data = {
            'client_id': settings.AZURE_AD_CLIENT_ID,
            'client_secret': settings.AZURE_AD_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': settings.AZURE_AD_REDIRECT_URI,
            'scope': 'openid profile email User.Read Mail.Read Calendars.Read Files.Read'
        }
        
        token_response = requests.post(token_url, data=token_data)
        token_json = token_response.json()
        
        if 'access_token' not in token_json:
            return JsonResponse({
                'error': 'Token exchange failed',
                'response': token_json
            })
        
        access_token = token_json['access_token']
        
        # Decode token without verification to inspect
        try:
            unverified_payload = jwt.decode(access_token, options={"verify_signature": False})
            unverified_header = jwt.get_unverified_header(access_token)
            
            return JsonResponse({
                'token_exchange': 'success',
                'token_header': unverified_header,
                'token_payload': unverified_payload,
                'azure_settings': {
                    'client_id': settings.AZURE_AD_CLIENT_ID,
                    'tenant_id': settings.AZURE_AD_TENANT_ID,
                    'redirect_uri': settings.AZURE_AD_REDIRECT_URI
                }
            }, indent=2)
            
        except Exception as decode_error:
            return JsonResponse({
                'error': 'Token decode failed',
                'decode_error': str(decode_error),
                'raw_token_response': token_json
            })
    
    except Exception as e:
        return JsonResponse({
            'error': 'Debug failed',
            'exception': str(e)
        })


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for managing users"""
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
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
        
        return queryset.select_related().prefetch_related('rbac_user_roles__role')

    @permission_required('user:view')
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @permission_required('user:view')
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @permission_required('user:create')
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @permission_required('user:edit')
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @permission_required('user:delete')
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    @permission_required('user:view')
    def stats(self, request):
        """Get user statistics"""
        from django.utils import timezone
        from datetime import timedelta
        
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
    @permission_required('user:view')
    def permission_summary(self, request, pk=None):
        """Get user permission summary using backend utility"""
        user = self.get_object()
        from permissions.utils import get_rbac_user_permissions_summary
        summary = get_rbac_user_permissions_summary(user)
        return Response(summary)

    @action(detail=False, methods=['post'])
    @permission_required('user:edit')
    def bulk_toggle_status(self, request):
        """Bulk activate/deactivate users"""
        user_ids = request.data.get('user_ids', [])
        is_active = request.data.get('is_active', True)
        
        updated_count = User.objects.filter(id__in=user_ids).update(is_active=is_active)
        
        return Response({
            'updated_count': updated_count,
            'message': f'Successfully {"activated" if is_active else "deactivated"} {updated_count} users'
        })

    @action(detail=False, methods=['post'])
    @permission_required('role:assign')
    def bulk_assign_role(self, request):
        """Bulk assign role to users"""
        user_ids = request.data.get('user_ids', [])
        role_id = request.data.get('role_id')
        
        from permissions.models import Role, UserRole
        
        try:
            role = Role.objects.get(id=role_id)
            assigned_count = 0
            
            for user_id in user_ids:
                user_role, created = UserRole.objects.get_or_create(
                    user_id=user_id,
                    role=role,
                    defaults={'assigned_by': request.user}
                )
                if created:
                    assigned_count += 1
            
            return Response({
                'assigned_count': assigned_count,
                'message': f'Successfully assigned role to {assigned_count} users'
            })
        except Role.DoesNotExist:
            return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    @permission_required('user:reset_password')
    def reset_password(self, request, pk=None):
        """Reset user password (for local users only)"""
        user = self.get_object()
        new_password = request.data.get('new_password')
        
        if not new_password:
            return Response({'error': 'New password is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if user.azure_id:
            return Response({'error': 'Cannot reset password for Azure SSO users'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(new_password)
        user.save()
        
        return Response({'message': 'Password reset successfully'})
