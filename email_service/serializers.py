# email_service/serializers.py
from rest_framework import serializers
from .models import EmailServiceSetting, EmailMessage, EmailAttachment, EmailSyncLog

class EmailServiceSettingSerializer(serializers.ModelSerializer):
    """
    Serializer for EmailServiceSetting (without sensitive data)
    """
    last_sync_status = serializers.SerializerMethodField()
    sync_logs_count = serializers.SerializerMethodField()
    
    class Meta:
        model = EmailServiceSetting
        fields = [
            'id', 'name', 'email', 'is_active', 'is_default',
            'sync_enabled', 'sync_interval_minutes', 'last_sync_at',
            'last_sync_status', 'sync_logs_count', 'created_at'
        ]
        read_only_fields = ['last_sync_at', 'created_at']

    def get_last_sync_status(self, obj):
        """Get the status of the last sync"""
        last_log = obj.sync_logs.first()
        return last_log.status if last_log else 'never_synced'

    def get_sync_logs_count(self, obj):
        """Get the count of sync logs"""
        return obj.sync_logs.count()


class EmailAttachmentSerializer(serializers.ModelSerializer):
    """
    Serializer for EmailAttachment
    """
    size_display = serializers.SerializerMethodField()
    
    class Meta:
        model = EmailAttachment
        fields = [
            'id', 'name', 'content_type', 'size', 'size_display',
            'is_inline', 'attachment_id', 'content_url'
        ]

    def get_size_display(self, obj):
        """Format file size for display"""
        if obj.size < 1024:
            return f"{obj.size} B"
        elif obj.size < 1024 * 1024:
            return f"{obj.size / 1024:.1f} KB"
        else:
            return f"{obj.size / (1024 * 1024):.1f} MB"


class EmailMessageSerializer(serializers.ModelSerializer):
    """
    Serializer for EmailMessage
    """
    from_display = serializers.SerializerMethodField()
    to_display = serializers.SerializerMethodField()
    service_name = serializers.CharField(source='service.name', read_only=True)
    attachments = EmailAttachmentSerializer(many=True, read_only=True)
    priority_display = serializers.CharField(source='priority_display', read_only=True)
    
    class Meta:
        model = EmailMessage
        fields = [
            'id', 'message_id', 'conversation_id', 'subject',
            'body_preview', 'body_content', 'body_content_type',
            'from_email', 'from_name', 'from_display',
            'to_recipients', 'to_display', 'cc_recipients', 'bcc_recipients',
            'importance', 'priority_display', 'is_read', 'is_draft',
            'has_attachments', 'categories', 'folder_name',
            'sent_datetime', 'received_datetime', 'service_name',
            'attachments', 'synced_at'
        ]

    def get_from_display(self, obj):
        """Get formatted sender display"""
        if obj.from_name:
            return f"{obj.from_name} <{obj.from_email}>"
        return obj.from_email

    def get_to_display(self, obj):
        """Get formatted recipients display"""
        recipients = []
        for recipient in obj.to_recipients:
            email_addr = recipient.get('emailAddress', {})
            name = email_addr.get('name', '')
            address = email_addr.get('address', '')
            if name:
                recipients.append(f"{name} <{address}>")
            else:
                recipients.append(address)
        return ', '.join(recipients)


class EmailMessageListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for email lists
    """
    from_display = serializers.SerializerMethodField()
    service_name = serializers.CharField(source='service.name', read_only=True)
    priority_display = serializers.CharField(source='priority_display', read_only=True)
    
    class Meta:
        model = EmailMessage
        fields = [
            'id', 'subject', 'from_email', 'from_name', 'from_display',
            'body_preview', 'importance', 'priority_display', 'is_read',
            'has_attachments', 'folder_name', 'received_datetime',
            'service_name', 'categories'
        ]

    def get_from_display(self, obj):
        """Get formatted sender display"""
        if obj.from_name:
            return f"{obj.from_name} <{obj.from_email}>"
        return obj.from_email


class EmailSyncLogSerializer(serializers.ModelSerializer):
    """
    Serializer for EmailSyncLog
    """
    service_name = serializers.CharField(source='service.name', read_only=True)
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = EmailSyncLog
        fields = [
            'id', 'service_name', 'status', 'sync_started_at',
            'sync_completed_at', 'duration', 'emails_processed',
            'emails_created', 'emails_updated', 'error_message'
        ]

    def get_duration(self, obj):
        """Calculate and format sync duration"""
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
        return "In progress"