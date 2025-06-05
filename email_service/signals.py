# email_service/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import EmailServiceSetting, EmailMessage
import logging

logger = logging.getLogger(__name__)

@receiver(pre_save, sender=EmailServiceSetting)
def handle_default_service_change(sender, instance, **kwargs):
    """Ensure only one default service exists"""
    if instance.is_default:
        # Remove default flag from other services
        EmailServiceSetting.objects.filter(is_default=True).exclude(pk=instance.pk).update(is_default=False)

@receiver(post_save, sender=EmailServiceSetting)
def log_service_changes(sender, instance, created, **kwargs):
    """Log email service setting changes"""
    if created:
        logger.info(f"New email service created: {instance.name} ({instance.email})")
    else:
        logger.info(f"Email service updated: {instance.name} ({instance.email})")

@receiver(post_save, sender=EmailMessage)
def log_email_sync(sender, instance, created, **kwargs):
    """Log email synchronization"""
    if created:
        logger.debug(f"New email synced: {instance.subject[:50]}... from {instance.from_email}")
