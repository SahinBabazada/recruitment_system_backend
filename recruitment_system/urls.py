from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('azure_auth.urls')),
    path('permissions/', include('permissions.urls')),
    path('mpr/', include('mpr.urls')),
]