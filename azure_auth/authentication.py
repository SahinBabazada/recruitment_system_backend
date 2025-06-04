# azure_auth/authentication.py (Simplified version)
import requests
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class AzureTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split(' ')[1]
        
        try:
            # Validate token by making a request to Microsoft Graph
            user = self.get_user_from_token(token)
            return (user, token)
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise AuthenticationFailed(f'Invalid token: {str(e)}')
    
    def get_user_from_token(self, token):
        try:
            # Validate token by calling Microsoft Graph API
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(
                f"{settings.GRAPH_API_ENDPOINT}/me",
                headers=headers,
                timeout=10
            )
            
            if response.status_code != 200:
                raise AuthenticationFailed('Token validation failed - invalid or expired token')
            
            user_info = response.json()
            azure_id = user_info.get('id')
            
            if not azure_id:
                raise AuthenticationFailed('Invalid user information from Microsoft Graph')
            
            # Find user in database
            try:
                user = User.objects.get(azure_id=azure_id)
                # Update access token
                user.access_token = token
                user.save()
                return user
            except User.DoesNotExist:
                raise AuthenticationFailed('User not found in database')
                
        except requests.RequestException as e:
            logger.error(f"Failed to validate token with Microsoft Graph: {str(e)}")
            raise AuthenticationFailed('Token validation failed')