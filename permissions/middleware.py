# permissions/middleware.py
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.urls import resolve
import json

class PermissionMiddleware(MiddlewareMixin):
    """
    Middleware to check permissions based on URL patterns
    """
    
    # Define URL pattern to permission mapping
    URL_PERMISSIONS = {
        # MPR endpoints
        'mpr-list': {'GET': 'mpr:view', 'POST': 'mpr:create'},
        'mpr-detail': {
            'GET': 'mpr:view',
            'PUT': 'mpr:edit',
            'PATCH': 'mpr:edit',
            'DELETE': 'mpr:delete'
        },
        
        # Interview endpoints
        'interview-list': {'GET': 'interview:view', 'POST': 'interview:create'},
        'interview-detail': {
            'GET': 'interview:view',
            'PUT': 'interview:edit',
            'PATCH': 'interview:edit',
            'DELETE': 'interview:delete'
        },
        
        # Candidate endpoints
        'candidate-list': {'GET': 'candidate:view', 'POST': 'candidate:create'},
        'candidate-detail': {
            'GET': 'candidate:view',
            'PUT': 'candidate:edit',
            'PATCH': 'candidate:edit',
            'DELETE': 'candidate:delete'
        },
        
        # Add more URL patterns as needed
    }
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Skip permission check for non-API endpoints
        if not request.path.startswith('/api/'):
            return None
        
        # Skip for unauthenticated requests (let authentication handle it)
        if not request.user.is_authenticated:
            return None
        
        try:
            # Get URL name from resolver
            resolver_match = resolve(request.path)
            url_name = resolver_match.url_name
            
            # Check if URL requires permission
            if url_name in self.URL_PERMISSIONS:
                method_permissions = self.URL_PERMISSIONS[url_name]
                required_permission = method_permissions.get(request.method)
                
                if required_permission and not request.user.has_permission(required_permission):
                    return JsonResponse({
                        'error': 'Permission denied',
                        'required_permission': required_permission,
                        'url_name': url_name,
                        'method': request.method
                    }, status=403)
        
        except Exception:
            # If URL resolution fails, continue without permission check
            pass
        
        return None