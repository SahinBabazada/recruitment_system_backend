# azure_auth/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import AppUser

@admin.register(AppUser)
class AppUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'azure_id', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'azure_id')
    filter_horizontal = ('groups',)  # Add this line - only keep groups
    
    fieldsets = UserAdmin.fieldsets + (
        ('Azure Information', {
            'fields': ('azure_id', 'access_token', 'refresh_token', 'token_expires_at')
        }),
    )