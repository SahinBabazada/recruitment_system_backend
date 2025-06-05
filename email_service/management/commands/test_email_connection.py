# email_service/management/commands/test_email_connection.py
from django.core.management.base import BaseCommand
from email_service.models import EmailServiceSetting
from email_service.services import EmailSyncService

class Command(BaseCommand):
    help = 'Test email service connection to Graph API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--service',
            type=str,
            help='Test specific service (by name or email)',
        )

    def handle(self, *args, **options):
        service_filter = options.get('service')

        if service_filter:
            services = EmailServiceSetting.objects.filter(
                models.Q(name__icontains=service_filter) | 
                models.Q(email__icontains=service_filter),
                is_active=True
            )
        else:
            services = EmailServiceSetting.objects.filter(is_active=True)

        if not services.exists():
            self.stdout.write(
                self.style.WARNING('No email services found')
            )
            return

        for service in services:
            self.stdout.write(f'\nTesting connection for: {service.name} ({service.email})')
            
            try:
                sync_service = EmailSyncService(service)
                result = sync_service.test_connection()
                
                if result['success']:
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ {result["message"]}')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'✗ {result["error"]}')
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Connection test failed: {str(e)}')
                )