# permissions/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PermissionViewSet, RoleViewSet, UserRoleViewSet, UserPermissionViewSet

router = DefaultRouter()
router.register(r'permissions', PermissionViewSet)
router.register(r'roles', RoleViewSet)
router.register(r'user-roles', UserRoleViewSet, basename='userrole')
router.register(r'user-permissions', UserPermissionViewSet, basename='userpermission')

urlpatterns = [
    path('api/', include(router.urls)),
]