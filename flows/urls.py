# flows/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FlowViewSet, FlowExecutionViewSet

router = DefaultRouter()
router.register(r'flows', FlowViewSet, basename='flow')
router.register(r'executions', FlowExecutionViewSet, basename='flow-execution')

urlpatterns = [
    path('api/', include(router.urls)),
]