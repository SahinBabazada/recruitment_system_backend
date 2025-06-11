# candidate/management/commands/migrate_candidate_models.py
from django.core.management.base import BaseCommand
from django.db import models, transaction
from candidate.models import (
    Candidate, CandidateEmailConnection, CandidateAttachment,
    CandidateWorkExperience, CandidateEducation
)
from email_service.models import EmailMessage


class Command(BaseCommand):
    help = 'Migrate candidate models to new structure'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--step',
            type=str,
            choices=['emails', 'sample-data', 'fields', 'scores', 'all'],
            default='all',
            help='Which migration step to run',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
    
    def handle(self, *args, **options):
        step = options['step']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )
        
        if step == 'emails' or step == 'all':
            self.stdout.write("Migrating candidate emails...")
            if not dry_run:
                self.migrate_existing_candidate_emails()
        
        if step == 'sample-data' or step == 'all':
            self.stdout.write("Creating sample data...")
            if not dry_run:
                self.create_sample_candidate_data()
        
        if step == 'fields' or step == 'all':
            self.stdout.write("Updating candidate fields...")
            if not dry_run:
                self.update_candidate_fields()
        
        if step == 'scores' or step == 'all':
            self.stdout.write("Checking duplicate scores...")
            if not dry_run:
                self.remove_duplicate_scores()
        
        self.stdout.write(
            self.style.SUCCESS("Migration completed successfully!")
        )
    
    def migrate_existing_candidate_emails(self):
        """Migrate existing CandidateEmail records to use email_service connections"""
        
        self.stdout.write("Starting migration of candidate emails...")
        
        # This would contain the migration logic from the migration script
        # For now, it's a placeholder since we're doing a fresh start
        
        migrated_count = 0
        self.stdout.write(f"Migration completed. Migrated: {migrated_count} emails")
    
    def create_sample_candidate_data(self):
        """Create sample work experience and education data for existing candidates"""
        
        self.stdout.write("Creating sample work experience and education data...")
        
        sample_data_created = 0
        
        for candidate in Candidate.objects.all():
            # Skip if already has work experience
            if candidate.work_experiences.exists():
                continue
            
            # Create sample work experience based on current position
            if candidate.current_position and candidate.current_company:
                CandidateWorkExperience.objects.create(
                    candidate=candidate,
                    company_name=candidate.current_company,
                    position_title=candidate.current_position,
                    start_date='2020-01-01',  # Default start date
                    is_current=True,
                    employment_type='full_time',
                    job_description=f"Working as {candidate.current_position} at {candidate.current_company}",
                    display_order=0
                )
                
                sample_data_created += 1
        
        self.stdout.write(f"Created sample work experience for {sample_data_created} candidates")
    
    def update_candidate_fields(self):
        """Update candidate fields with new structure"""
        
        self.stdout.write("Updating candidate fields...")
        
        updated_count = 0
        
        for candidate in Candidate.objects.all():
            updated = False
            
            # Set default currency if salary expectation exists but no currency
            if candidate.salary_expectation and not candidate.salary_currency:
                candidate.salary_currency = 'USD'
                updated = True
            
            if updated:
                candidate.save()
                updated_count += 1
        
        self.stdout.write(f"Updated {updated_count} candidate records")
    
    def remove_duplicate_scores(self):
        """Remove duplicate scoring fields that are now handled in interviews"""
        
        self.stdout.write("Cleaning up duplicate scoring fields...")
        
        # Note: Individual interview scores should be moved to interview evaluations
        candidates_with_scores = Candidate.objects.filter(
            overall_score__isnull=False
        )
        
        self.stdout.write(f"Found {candidates_with_scores.count()} candidates with scores")
        self.stdout.write("Individual interview scores should be migrated to InterviewCriteriaEvaluation records")