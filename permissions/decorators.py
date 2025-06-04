# permissions/decorators.py
from functools import wraps
from django.http import JsonResponse

def permission_required(permission_name):
    """
    Decorator to check if user has specific permission
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Authentication required'}, status=401)
            
            if not hasattr(request.user, 'has_permission') or not request.user.has_permission(permission_name):
                return JsonResponse({
                    'error': 'Permission denied',
                    'required_permission': permission_name
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def any_permission_required(permission_names):
    """
    Decorator to check if user has any of the specified permissions
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Authentication required'}, status=401)
            
            if not hasattr(request.user, 'has_any_permission') or not request.user.has_any_permission(permission_names):
                return JsonResponse({
                    'error': 'Permission denied',
                    'required_permissions': permission_names
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def module_access_required(module_name):
    """
    Decorator to check if user has any permission for a specific module
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Authentication required'}, status=401)
            
            if not hasattr(request.user, 'has_module_access') or not request.user.has_module_access(module_name):
                return JsonResponse({
                    'error': 'Module access denied',
                    'required_module': module_name
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
