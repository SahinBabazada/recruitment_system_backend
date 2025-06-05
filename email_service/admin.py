# email_service/admin.py
from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.utils.html import format_html
from django.utils import timezone
from django import forms
from .models import EmailServiceSetting, EmailMessage, EmailAttachment, EmailSyncLog
from .services import EmailSyncService

class EmailServiceSettingForm(forms.ModelForm):
    """Custom form for EmailServiceSetting with password field"""
    password_field = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter service account password'}),
        required=False,
        help_text='Leave blank to keep current password',
        label='Password'
    )
    
    class Meta:
        model = EmailServiceSetting
        fields = ['name', 'email', 'is_active', 'is_default', 'tenant_id', 
                 'client_id', 'client_secret', 'sync_enabled', 'sync_interval_minutes']
        widgets = {
            'client_secret': forms.PasswordInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If editing existing object, change help text
        if self.instance and self.instance.pk:
            self.fields['password_field'].help_text = 'Leave blank to keep current password'
            self.fields['password_field'].required = False
        else:
            self.fields['password_field'].help_text = 'Enter password for service account (required)'
            self.fields['password_field'].required = True

@admin.register(EmailServiceSetting)
class EmailServiceSettingAdmin(admin.ModelAdmin):
    form = EmailServiceSettingForm
    list_display = [
        'name', 'email', 'is_active', 'is_default', 
        'last_sync_status', 'last_sync_at', 'sync_actions'
    ]
    list_filter = ['is_active', 'is_default', 'sync_enabled', 'created_at']
    search_fields = ['name', 'email', 'tenant_id']
    readonly_fields = ['last_sync_at', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'email', 'password_field', 'is_active', 'is_default')
        }),
        ('Azure/Graph API Configuration', {
            'fields': ('tenant_id', 'client_id', 'client_secret'),
            'classes': ('collapse',)
        }),
        ('Sync Settings', {
            'fields': ('sync_enabled', 'sync_interval_minutes', 'last_sync_at'),
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )

    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        obj.updated_by = request.user
        
        # Handle password
        password = form.cleaned_data.get('password_field')
        if password:
            obj.set_password(password)
        elif not change:  # New object must have password
            messages.error(request, 'Password is required for new email service settings.')
            return
        
        super().save_model(request, obj, form, change)
        
        # Display success message with credentials
        if password:
            messages.success(
                request, 
                f'Email service "{obj.name}" saved successfully. Password has been encrypted and stored securely.'
            )

    def last_sync_status(self, obj):
        """Display last sync status with color coding"""
        last_log = obj.sync_logs.first()
        if not last_log:
            return format_html('<span style="color: gray;">Never synced</span>')
        
        color_map = {
            'completed': 'green',
            'running': 'blue',
            'failed': 'red',
            'cancelled': 'orange'
        }
        color = color_map.get(last_log.status, 'gray')
        
        return format_html(
            '<span style="color: {};">{}</span><br><small>{} emails processed</small>',
            color,
            last_log.get_status_display(),
            last_log.emails_processed
        )
    last_sync_status.short_description = 'Last Sync Status'

    def sync_actions(self, obj):
        """Display sync action buttons"""
        if not obj.pk:
            return '-'
        
        return format_html(
            '<a class="button" href="{}sync/{}" onclick="return confirm(\'Start email sync?\')">Sync Now</a> '
            '<a class="button" href="{}logs/{}" target="_blank">View Logs</a>',
            '/admin/email_service/emailservicesetting/',
            obj.pk,
            '/admin/email_service/emailservicesetting/',
            obj.pk
        )
    sync_actions.short_description = 'Actions'
    sync_actions.allow_tags = True

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('sync/<int:service_id>/', self.admin_site.admin_view(self.sync_emails_view), name='sync-emails'),
            path('logs/<int:service_id>/', self.admin_site.admin_view(self.view_logs), name='view-sync-logs'),
            path('test-connection/<int:service_id>/', self.admin_site.admin_view(self.test_connection), name='test-connection'),
        ]
        return custom_urls + urls

    def sync_emails_view(self, request, service_id):
        """Start email synchronization"""
        try:
            service = EmailServiceSetting.objects.get(pk=service_id)
            sync_service = EmailSyncService(service)
            
            if request.method == 'POST':
                # Start async sync
                result = sync_service.sync_emails()
                if result['success']:
                    messages.success(request, f"Email sync started for {service.name}")
                else:
                    messages.error(request, f"Failed to start sync: {result['error']}")
                return redirect('admin:email_service_emailservicesetting_changelist')
            
            # Show confirmation page
            context = {
                'service': service,
                'title': f'Sync Emails - {service.name}',
                'opts': self.model._meta,
            }
            return render(request, 'admin/email_service/sync_confirm.html', context)
            
        except EmailServiceSetting.DoesNotExist:
            messages.error(request, 'Email service not found')
            return redirect('admin:email_service_emailservicesetting_changelist')

    def view_logs(self, request, service_id):
        """View sync logs for a service"""
        try:
            service = EmailServiceSetting.objects.get(pk=service_id)
            logs = service.sync_logs.all()[:20]  # Latest 20 logs
            
            context = {
                'service': service,
                'logs': logs,
                'title': f'Sync Logs - {service.name}',
                'opts': self.model._meta,
            }
            return render(request, 'admin/email_service/sync_logs.html', context)
            
        except EmailServiceSetting.DoesNotExist:
            messages.error(request, 'Email service not found')
            return redirect('admin:email_service_emailservicesetting_changelist')

    def test_connection(self, request, service_id):
        """Test Graph API connection"""
        try:
            service = EmailServiceSetting.objects.get(pk=service_id)
            sync_service = EmailSyncService(service)
            
            result = sync_service.test_connection()
            
            return JsonResponse({
                'success': result['success'],
                'message': result.get('message', ''),
                'error': result.get('error', '')
            })
            
        except EmailServiceSetting.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Service not found'})


@admin.register(EmailMessage)
class EmailMessageAdmin(admin.ModelAdmin):
    list_display = [
        'subject_truncated', 'from_email', 'from_name', 'service',
        'received_datetime', 'is_read', 'has_attachments', 'importance'
    ]
    list_filter = [
        'service', 'is_read', 'has_attachments', 'importance',
        'received_datetime', 'folder_name'
    ]
    search_fields = ['subject', 'from_email', 'from_name', 'body_preview']
    readonly_fields = [
        'message_id', 'conversation_id', 'sent_datetime', 'received_datetime',
        'created_datetime', 'last_modified_datetime', 'synced_at', 'updated_at'
    ]
    list_per_page = 50
    
    fieldsets = (
        ('Email Information', {
            'fields': ('service', 'message_id', 'conversation_id')
        }),
        ('Content', {
            'fields': ('subject', 'body_preview', 'body_content', 'body_content_type')
        }),
        ('Recipients', {
            'fields': ('from_email', 'from_name', 'to_recipients', 'cc_recipients', 'bcc_recipients')
        }),
        ('Properties', {
            'fields': ('importance', 'is_read', 'is_draft', 'has_attachments', 'categories')
        }),
        ('Folder & Timestamps', {
            'fields': (
                'folder_id', 'folder_name',
                'sent_datetime', 'received_datetime', 'created_datetime',
                'last_modified_datetime', 'synced_at', 'updated_at'
            ),
            'classes': ('collapse',)
        })
    )

    def subject_truncated(self, obj):
        return obj.subject[:60] + '...' if len(obj.subject) > 60 else obj.subject
    subject_truncated.short_description = 'Subject'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('service')


@admin.register(EmailAttachment)
class EmailAttachmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'email_subject', 'content_type', 'size_display', 'is_inline']
    list_filter = ['content_type', 'is_inline', 'created_at']
    search_fields = ['name', 'email__subject', 'email__from_email']
    readonly_fields = ['attachment_id', 'size', 'created_at']

    def email_subject(self, obj):
        return obj.email.subject[:50] + '...' if len(obj.email.subject) > 50 else obj.email.subject
    email_subject.short_description = 'Email Subject'

    def size_display(self, obj):
        if obj.size < 1024:
            return f"{obj.size} B"
        elif obj.size < 1024 * 1024:
            return f"{obj.size / 1024:.1f} KB"
        else:
            return f"{obj.size / (1024 * 1024):.1f} MB"
    size_display.short_description = 'Size'


@admin.register(EmailSyncLog)
class EmailSyncLogAdmin(admin.ModelAdmin):
    list_display = [
        'service', 'status', 'sync_started_at', 'duration_display',
        'emails_processed', 'emails_created', 'emails_updated'
    ]
    list_filter = ['status', 'sync_started_at', 'service']
    readonly_fields = [
        'sync_started_at', 'sync_completed_at', 'emails_processed',
        'emails_created', 'emails_updated', 'error_message', 'error_details'
    ]
    list_per_page = 50
    
    fieldsets = (
        ('Sync Information', {
            'fields': ('service', 'status', 'sync_started_at', 'sync_completed_at')
        }),
        ('Results', {
            'fields': ('emails_processed', 'emails_created', 'emails_updated')
        }),
        ('Errors', {
            'fields': ('error_message', 'error_details'),
            'classes': ('collapse',)
        })
    )

    def duration_display(self, obj):
        if obj.sync_completed_at:
            duration = obj.sync_completed_at - obj.sync_started_at
            total_seconds = int(duration.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        else:
            duration = timezone.now() - obj.sync_started_at
            return f"Running for {int(duration.total_seconds())}s"
    duration_display.short_description = 'Duration'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('service')

# Customize admin site
admin.site.site_header = "Email Service Administration"
admin.site.site_title = "Email Admin"
admin.site.index_title = "Welcome to Email Service Administration"