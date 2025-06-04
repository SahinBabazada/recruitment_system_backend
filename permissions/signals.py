# permissions/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserRole, UserPermission, Role
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

@receiver(post_save, sender=UserRole)
def log_role_assignment(sender, instance, created, **kwargs):
    """Log when roles are assigned to users"""
    if created:
        logger.info(
            f"Role '{instance.role.name}' assigned to user '{instance.user.username}' "
            f"by {instance.assigned_by.username if instance.assigned_by else 'system'}"
        )

@receiver(post_delete, sender=UserRole)
def log_role_removal(sender, instance, **kwargs):
    """Log when roles are removed from users"""
    logger.info(
        f"Role '{instance.role.name}' removed from user '{instance.user.username}'"
    )

@receiver(post_save, sender=UserPermission)
def log_permission_change(sender, instance, created, **kwargs):
    """Log when permissions are granted/denied to users"""
    action = "granted" if instance.granted else "denied"
    log_action = "assigned" if created else "updated"
    
    logger.info(
        f"Permission '{instance.permission.name}' {action} to user '{instance.user.username}' "
        f"({log_action}) by {instance.granted_by.username if instance.granted_by else 'system'}"
    )