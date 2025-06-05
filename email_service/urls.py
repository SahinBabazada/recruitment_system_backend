# email_service/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'services', views.EmailServiceSettingViewSet, basename='emailservice')

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    
    # Email endpoints
    path('api/emails/', views.get_emails, name='get-emails'),
    path('api/emails/<int:email_id>/', views.get_email_detail, name='get-email-detail'),
    path('api/emails/<int:email_id>/mark-read/', views.mark_email_read, name='mark-email-read'),
    path('api/emails/bulk-mark-read/', views.bulk_mark_read, name='bulk-mark-read'),
    path('api/emails/search/', views.search_emails, name='search-emails'),
    
    # Sync endpoints
    path('api/sync/trigger/', views.trigger_sync, name='trigger-sync'),
    path('api/sync/status/', views.sync_status, name='sync-status'),
    
    # Folder/category endpoints
    path('api/folders/counts/', views.get_folder_counts, name='folder-counts'),
]