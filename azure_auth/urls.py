# azure_auth/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.azure_login, name='azure_login'),
    path('logout/', views.azure_logout, name='azure_logout'),
    path('callback/', views.azure_callback, name='azure_callback'),
    path('profile/', views.user_profile, name='user_profile'),
    path('emails/', views.user_emails, name='user_emails'),
    path('calendar/', views.user_calendar, name='user_calendar'),
    path('files/', views.user_files, name='user_files'),
    path('debug-auth/', views.debug_auth, name='debug_auth'),

    #Local auth URLs
    path('local/login/', views.local_login, name='local_login'),
    path('local/register/', views.local_register, name='local_register'),
]