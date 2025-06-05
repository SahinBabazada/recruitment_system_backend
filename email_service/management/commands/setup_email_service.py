# email_service/management/commands/setup_email_service.py
from django.core.management.base import BaseCommand
from email_service.models import EmailServiceSetting

class Command(BaseCommand):
    help = 'Set up initial email service configuration'

    def add_arguments(self, parser):
        parser.add_argument('--name', type=str, required=True, help='Service name')
        parser.add_argument('--email', type=str, required=True, help='Service email')
        parser.add_argument('--password', type=str, required=True, help='Service password')
        parser.add_argument('--tenant-id', type=str, required=True, help='Azure tenant ID')
        parser.add_argument('--client-id', type=str, required=True, help='Azure client ID')
        parser.add_argument('--client-secret', type=str, required=True, help='Azure client secret')
        parser.add_argument('--set-default', action='store_true', help='Set as default service')

    def handle(self, *args, **options):
        service = EmailServiceSetting.objects.create(
            name=options['name'],
            email=options['email'],
            tenant_id=options['tenant_id'],
            client_id=options['client_id'],
            client_secret=options['client_secret'],
            is_default=options['set_default'],
            is_active=True,
            sync_enabled=True
        )
        
        # Set password using encrypted storage
        service.set_password(options['password'])
        service.save()
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created email service: {service.name}')
        )