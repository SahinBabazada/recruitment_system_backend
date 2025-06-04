# mpr/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import MPR, MPRStatusHistory
import logging

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=MPR)
def track_status_changes(sender, instance, **kwargs):
    """Track status changes and create history records"""
    if instance.pk:  # Only for existing instances
        try:
            old_instance = MPR.objects.get(pk=instance.pk)
            if old_instance.status != instance.status:
                # Store the old status for later use in post_save
                instance._old_status = old_instance.status
                instance._status_changed = True
            else:
                instance._status_changed = False
        except MPR.DoesNotExist:
            instance._status_changed = False
    else:
        instance._status_changed = False


@receiver(post_save, sender=MPR)
def create_status_history(sender, instance, created, **kwargs):
    """Create status history record when status changes"""
    if not created and getattr(instance, '_status_changed', False):
        old_status = getattr(instance, '_old_status', None)
        if old_status:
            MPRStatusHistory.objects.create(
                mpr=instance,
                from_status=old_status,
                to_status=instance.status,
                changed_by=getattr(instance, 'updated_by', None) or instance.created_by,
                reason=f'Status changed from {old_status} to {instance.status}'
            )
            
            logger.info(
                f"MPR {instance.mpr_number} status changed from {old_status} to {instance.status}"
            )

    # Log MPR creation
    if created:
        logger.info(
            f"New MPR created: {instance.mpr_number} by {instance.created_by.username}"
        )


@receiver(post_save, sender=MPR)
def send_notifications(sender, instance, created, **kwargs):
    """Send notifications for MPR events"""
    # This is a placeholder for future notification system
    # You can implement email notifications, in-app notifications, etc.
    
    if created:
        # Notify relevant users about new MPR
        logger.info(f"TODO: Send notification for new MPR {instance.mpr_number}")
    
    elif getattr(instance, '_status_changed', False):
        # Notify relevant users about status change
        if instance.status == 'pending':
            # Notify approvers
            logger.info(f"TODO: Notify approvers about MPR {instance.mpr_number} pending approval")
        elif instance.status == 'approved':
            # Notify recruiter and created_by
            logger.info(f"TODO: Notify about MPR {instance.mpr_number} approval")
        elif instance.status == 'rejected':
            # Notify created_by about rejection
            logger.info(f"TODO: Notify about MPR {instance.mpr_number} rejection")