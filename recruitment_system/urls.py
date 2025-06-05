# recruitment_system/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('azure_auth.urls')),
    path('mpr/', include('mpr.urls')),
    path('permissions/', include('permissions.urls')),
    path('email_service/', include('email_service.urls')),
]

# Add debug toolbar URLs for development
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
