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

    # Candidate integration endpoints
    path('api/emails/<int:email_id>/create-candidate/', views.create_candidate_from_email, name='create-candidate-from-email'),
    path('api/emails/with-candidate-status/', views.get_emails_with_candidate_status, name='get-emails-with-candidate-status'),
    path('api/emails/by-candidate/', views.get_candidate_emails, name='get-candidate-emails'),
]