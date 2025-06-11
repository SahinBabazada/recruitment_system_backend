# candidate/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Candidate, CandidateAttachment, CandidateStatusUpdate

User = get_user_model()


@receiver(post_save, sender=Candidate)
def sync_candidate_emails_on_create(sender, instance, created, **kwargs):
    """Automatically sync emails when a new candidate is created"""
    if created:
        # Import here to avoid circular imports
        from .utils.email_integration import EmailSyncService
        
        # Run email sync in background (you might want to use Celery for this)
        try:
            EmailSyncService.sync_new_candidate_emails(instance)
        except Exception as e:
            # Log error but don't fail candidate creation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to sync emails for candidate {instance.email}: {str(e)}")


@receiver(post_save, sender=CandidateAttachment)
def handle_primary_cv_uniqueness(sender, instance, created, **kwargs):
    """Ensure only one primary CV per candidate"""
    if instance.is_primary_cv:
        # Remove primary flag from other CVs for this candidate
        CandidateAttachment.objects.filter(
            candidate=instance.candidate,
            is_primary_cv=True
        ).exclude(pk=instance.pk).update(is_primary_cv=False)


@receiver(pre_save, sender=Candidate)
def create_status_update_on_change(sender, instance, **kwargs):
    """Create status update record when hiring status changes"""
    if instance.pk:  # Only for existing instances
        try:
            old_instance = Candidate.objects.get(pk=instance.pk)
            if old_instance.hiring_status != instance.hiring_status:
                # Status has changed - we'll create the update record after save
                instance._status_changed = True
                instance._previous_status = old_instance.hiring_status
        except Candidate.DoesNotExist:
            pass


@receiver(post_save, sender=Candidate)
def create_status_update_after_save(sender, instance, created, **kwargs):
    """Create status update record after candidate save"""
    if not created and hasattr(instance, '_status_changed') and instance._status_changed:
        CandidateStatusUpdate.objects.create(
            candidate=instance,
            previous_status=instance._previous_status,
            new_status=instance.hiring_status,
            reason="Status updated",
            updated_by=None  # System update, no specific user
        )
        
        # Clean up temporary attributes
        delattr(instance, '_status_changed')
        delattr(instance, '_previous_status')