# email_service/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from cryptography.fernet import Fernet
from django.conf import settings
import base64
import json
from django.conf import settings

User = get_user_model()

class EmailServiceSetting(models.Model):
    """
    Model to store email service credentials for Graph API access
    """
    name = models.CharField(max_length=100, unique=True, help_text="Service name identifier")
    email = models.EmailField(help_text="Service account email for Graph API")
    
    # Encrypted password field
    encrypted_password = models.TextField(help_text="Encrypted password for the service account")
    
    # Azure/Graph API specific settings
    tenant_id = models.CharField(max_length=100, help_text="Azure tenant ID")
    client_id = models.CharField(max_length=100, help_text="Azure client ID")
    client_secret = models.TextField(help_text="Azure client secret")
    
    # Status and configuration
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False, help_text="Default service for email operations")
    
    # Sync settings
    last_sync_at = models.DateTimeField(null=True, blank=True)
    sync_enabled = models.BooleanField(default=True)
    sync_interval_minutes = models.IntegerField(default=15, help_text="Sync interval in minutes")
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_email_services')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_email_services')

    class Meta:
        db_table = 'email_service_settings'
        ordering = ['-is_default', 'name']
        verbose_name = 'Email Service Setting'
        verbose_name_plural = 'Email Service Settings'

    def __str__(self):
        return f"{self.name} ({self.email})"

    def clean(self):
        # Ensure only one default service
        if self.is_default:
            existing_default = EmailServiceSetting.objects.filter(is_default=True).exclude(pk=self.pk)
            if existing_default.exists():
                raise ValidationError("Only one default email service is allowed.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def set_password(self, raw_password):
        """Encrypt and store the password"""
        cipher_suite = Fernet(self._get_encryption_key())
        encrypted_password = cipher_suite.encrypt(raw_password.encode())
        self.encrypted_password = base64.b64encode(encrypted_password).decode()

    def get_password(self):
        """Decrypt and return the password"""
        try:
            cipher_suite = Fernet(self._get_encryption_key())
            encrypted_password = base64.b64decode(self.encrypted_password.encode())
            return cipher_suite.decrypt(encrypted_password).decode()
        except Exception:
            return None

    @staticmethod
    def _get_encryption_key():
        """Get or generate encryption key"""
        key = getattr(settings, 'EMAIL_SERVICE_ENCRYPTION_KEY', None)
        if not key:
            # Generate a new key if not set in settings
            key = Fernet.generate_key()
            # In production, this should be set in environment variables
        return key if isinstance(key, bytes) else key.encode()

    @classmethod
    def get_default_service(cls):
        """Get the default email service"""
        return cls.objects.filter(is_default=True, is_active=True).first()


class EmailMessage(models.Model):
    """
    Model to store email messages retrieved from Graph API
    """
    service = models.ForeignKey(EmailServiceSetting, on_delete=models.CASCADE, related_name='emails')
    
    # Email identifiers
    message_id = models.CharField(max_length=255, unique=True, help_text="Unique message ID from Graph API")
    conversation_id = models.CharField(max_length=255, db_index=True, help_text="Conversation ID from Graph API")
    
    # Email content
    subject = models.TextField()
    body_preview = models.TextField(blank=True)
    body_content = models.TextField(blank=True)
    body_content_type = models.CharField(max_length=10, choices=[('text', 'Text'), ('html', 'HTML')], default='html')
    
    # Sender and recipients
    from_email = models.EmailField()
    from_name = models.CharField(max_length=255, blank=True)
    to_recipients = models.JSONField(default=list, help_text="List of To recipients")
    cc_recipients = models.JSONField(default=list, help_text="List of CC recipients")
    bcc_recipients = models.JSONField(default=list, help_text="List of BCC recipients")
    
    # Message properties
    importance = models.CharField(max_length=10, choices=[
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High')
    ], default='normal')
    
    is_read = models.BooleanField(default=False)
    is_draft = models.BooleanField(default=False)
    has_attachments = models.BooleanField(default=False)
    
    # Categories and folders
    categories = models.JSONField(default=list, help_text="Email categories")
    folder_id = models.CharField(max_length=255, blank=True)
    folder_name = models.CharField(max_length=255, blank=True)
    
    # Timestamps
    sent_datetime = models.DateTimeField()
    received_datetime = models.DateTimeField()
    created_datetime = models.DateTimeField()
    last_modified_datetime = models.DateTimeField()
    
    # Sync tracking
    synced_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'email_messages'
        ordering = ['-received_datetime']
        indexes = [
            models.Index(fields=['service', 'received_datetime']),
            models.Index(fields=['from_email']),
            models.Index(fields=['is_read']),
            models.Index(fields=['message_id']),
            models.Index(fields=['conversation_id']),
        ]

    def __str__(self):
        return f"{self.subject[:50]}... - {self.from_email}"

    @property
    def priority_display(self):
        """Convert importance to priority for frontend compatibility"""
        mapping = {'low': 'low', 'normal': 'medium', 'high': 'high'}
        return mapping.get(self.importance, 'medium')

    def to_dict(self):
        """Convert to dictionary for frontend consumption"""
        return {
            'id': str(self.id),
            'subject': self.subject,
            'from': self.from_email,
            'fromName': self.from_name,
            'to': ', '.join([r.get('emailAddress', {}).get('address', '') for r in self.to_recipients]),
            'content': self.body_preview,
            'timestamp': self.received_datetime.isoformat(),
            'read': self.is_read,
            'category': self.folder_name.lower() if self.folder_name else 'inbox',
            'priority': self.priority_display,
            'avatar': self.from_name[:2].upper() if self.from_name else 'UN',
            'hasAttachment': self.has_attachments,
            'labels': self.categories,
            'attachments': []  # Will be populated by attachments if needed
        }


class EmailAttachment(models.Model):
    """
    Model to store email attachment information
    """
    email = models.ForeignKey(EmailMessage, on_delete=models.CASCADE, related_name='attachments')
    attachment_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.IntegerField(help_text="Size in bytes")
    is_inline = models.BooleanField(default=False)
    
    # Content (for small attachments, larger ones should be stored separately)
    content_bytes = models.BinaryField(null=True, blank=True)
    content_url = models.URLField(blank=True, help_text="URL to download attachment")
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'email_attachments'
        unique_together = ['email', 'attachment_id']

    def __str__(self):
        return f"{self.name} - {self.email.subject[:30]}"


class EmailSyncLog(models.Model):
    """
    Model to track email synchronization status and errors
    """
    service = models.ForeignKey(EmailServiceSetting, on_delete=models.CASCADE, related_name='sync_logs')
    
    sync_started_at = models.DateTimeField(auto_now_add=True)
    sync_completed_at = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=[
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled')
    ], default='running')
    
    emails_processed = models.IntegerField(default=0)
    emails_created = models.IntegerField(default=0)
    emails_updated = models.IntegerField(default=0)
    
    error_message = models.TextField(blank=True)
    error_details = models.JSONField(default=dict)
    
    class Meta:
        db_table = 'email_sync_logs'
        ordering = ['-sync_started_at']

    def __str__(self):
        return f"Sync {self.service.name} - {self.status} - {self.sync_started_at}"

    @property
    def duration(self):
        """Calculate sync duration"""
        if self.sync_completed_at:
            return self.sync_completed_at - self.sync_started_at
        return timezone.now() - self.sync_started_at