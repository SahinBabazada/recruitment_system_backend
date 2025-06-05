# email_service/tasks.py (Celery tasks for background sync)
from celery import shared_task
from .models import EmailServiceSetting
from .services import EmailSyncService
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def sync_emails_task(self, service_id, folder='inbox', max_emails=100, force_full_sync=False):
    """
    Celery task for background email synchronization
    """
    try:
        service = EmailServiceSetting.objects.get(id=service_id)
        sync_service = EmailSyncService(service)
        
        result = sync_service.sync_emails(
            folder=folder,
            max_emails=max_emails,
            force_full_sync=force_full_sync
        )
        
        logger.info(f"Email sync completed for {service.name}: {result}")
        return result
        
    except EmailServiceSetting.DoesNotExist:
        error_msg = f"Email service with ID {service_id} not found"
        logger.error(error_msg)
        raise Exception(error_msg)
    except Exception as e:
        logger.error(f"Email sync failed for service {service_id}: {str(e)}")
        raise

@shared_task
def auto_sync_all_services():
    """
    Celery task to automatically sync all active email services
    """
    services = EmailServiceSetting.objects.filter(is_active=True, sync_enabled=True)
    
    for service in services:
        try:
            sync_emails_task.delay(
                service_id=service.id,
                folder='inbox',
                max_emails=50,
                force_full_sync=False
            )
            logger.info(f"Queued sync task for service: {service.name}")
        except Exception as e:
            logger.error(f"Failed to queue sync task for service {service.name}: {str(e)}")

# Periodic task setup (add to celery.py)
from celery.schedules import crontab

app.conf.beat_schedule = {
    'auto-sync-emails': {
        'task': 'email_service.tasks.auto_sync_all_services',
        'schedule': crontab(minute='*/15'),  # Run every 15 minutes
    },
}
app.conf.timezone = 'UTC'