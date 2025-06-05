# email_service/management/commands/sync_emails.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from email_service.models import EmailServiceSetting
from email_service.services import EmailSyncService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sync emails from Graph API for all active email services'

    def add_arguments(self, parser):
        parser.add_argument(
            '--service',
            type=str,
            help='Sync emails for specific service (by name or email)',
        )
        parser.add_argument(
            '--folder',
            type=str,
            default='inbox',
            help='Folder to sync (default: inbox)',
        )
        parser.add_argument(
            '--max-emails',
            type=int,
            default=100,
            help='Maximum number of emails to sync (default: 100)',
        )
        parser.add_argument(
            '--force-full-sync',
            action='store_true',
            help='Force full sync (ignore last sync time)',
        )

    def handle(self, *args, **options):
        service_filter = options.get('service')
        folder = options['folder']
        max_emails = options['max_emails']
        force_full_sync = options['force_full_sync']

        # Get services to sync
        if service_filter:
            services = EmailServiceSetting.objects.filter(
                models.Q(name__icontains=service_filter) | 
                models.Q(email__icontains=service_filter),
                is_active=True
            )
        else:
            services = EmailServiceSetting.objects.filter(is_active=True, sync_enabled=True)

        if not services.exists():
            self.stdout.write(
                self.style.WARNING('No active email services found for syncing')
            )
            return

        self.stdout.write(f'Found {services.count()} service(s) to sync')

        total_processed = 0
        total_created = 0
        total_updated = 0

        for service in services:
            self.stdout.write(f'\nSyncing emails for: {service.name} ({service.email})')
            
            try:
                sync_service = EmailSyncService(service)
                result = sync_service.sync_emails(
                    folder=folder,
                    max_emails=max_emails,
                    force_full_sync=force_full_sync
                )

                if result['success']:
                    processed = result['processed']
                    created = result['created']
                    updated = result['updated']
                    
                    total_processed += processed
                    total_created += created
                    total_updated += updated
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ Synced {processed} emails ({created} new, {updated} updated)'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'✗ Sync failed: {result["error"]}')
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Sync failed with exception: {str(e)}')
                )
                logger.error(f'Email sync failed for {service.name}: {str(e)}')

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSync completed: {total_processed} total processed, '
                f'{total_created} created, {total_updated} updated'
            )
        )
