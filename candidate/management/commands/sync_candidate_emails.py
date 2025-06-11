# candidate/management/commands/sync_candidate_emails.py
from django.core.management.base import BaseCommand
from candidate.utils.email_integration import EmailSyncService


class Command(BaseCommand):
    help = 'Sync emails from email service with candidates'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--candidate-email',
            type=str,
            help='Sync emails for specific candidate email',
        )
        parser.add_argument(
            '--days-back',
            type=int,
            default=30,
            help='Number of days back to sync (default: 30)',
        )
    
    def handle(self, *args, **options):
        candidate_email = options.get('candidate_email')
        days_back = options.get('days_back')
        
        self.stdout.write(f"Starting email sync...")
        
        if candidate_email:
            self.stdout.write(f"Syncing emails for: {candidate_email}")
        else:
            self.stdout.write(f"Syncing emails for all candidates")
        
        self.stdout.write(f"Looking back {days_back} days")
        
        result = EmailSyncService.sync_candidate_emails(
            candidate_email=candidate_email,
            days_back=days_back
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Email sync completed. "
                f"Processed: {result['processed_emails']} emails, "
                f"Created: {result['created_connections']} connections"
            )
        )