# permissions/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from .models import Permission, Role, UserRole, UserPermission
from .serializers import PermissionSerializer, RoleSerializer, UserRoleSerializer, UserPermissionSerializer

User = get_user_model()

class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        module = self.request.query_params.get('module')
        if module:
            queryset = queryset.filter(module=module)
        return queryset
    
    @action(detail=False, methods=['get'])
    def modules(self, request):
        """Get all available modules"""
        modules = Permission.objects.values_list('module', flat=True).distinct()
        return Response(list(modules))

class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if not hasattr(self.request.user, 'has_permission') or not self.request.user.has_permission('system:manage_service_roles'):
            queryset = queryset.filter(is_service=False)
        return queryset
    
    def perform_create(self, serializer):
        serializer.save()
    
    def perform_update(self, serializer):
        role = serializer.instance
        if role.is_service and not self.request.user.has_permission('system:manage_service_roles'):
            raise PermissionDenied("Cannot modify service roles")
        serializer.save()
    
    def perform_destroy(self, instance):
        if instance.is_service:
            raise PermissionDenied("Cannot delete service roles")
        instance.delete()
    
    @action(detail=True, methods=['post'])
    def add_permission(self, request, pk=None):
        """Add permission to role"""
        role = self.get_object()
        permission_id = request.data.get('permission_id')
        
        try:
            permission = Permission.objects.get(id=permission_id)
            role.permissions.add(permission)
            return Response({'status': 'permission added'})
        except Permission.DoesNotExist:
            return Response(
                {'error': 'Permission not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def remove_permission(self, request, pk=None):
        """Remove permission from role"""
        role = self.get_object()
        permission_id = request.data.get('permission_id')
        
        try:
            permission = Permission.objects.get(id=permission_id)
            role.permissions.remove(permission)
            return Response({'status': 'permission removed'})
        except Permission.DoesNotExist:
            return Response(
                {'error': 'Permission not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class UserRoleViewSet(viewsets.ModelViewSet):
    serializer_class = UserRoleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user_id = self.request.query_params.get('user_id')
        if user_id:
            return UserRole.objects.filter(user_id=user_id)
        return UserRole.objects.all()
    
    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)

class UserPermissionViewSet(viewsets.ModelViewSet):
    serializer_class = UserPermissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user_id = self.request.query_params.get('user_id')
        if user_id:
            return UserPermission.objects.filter(user_id=user_id)
        return UserPermission.objects.all()
    
    def perform_create(self, serializer):
        serializer.save(granted_by=self.request.user)