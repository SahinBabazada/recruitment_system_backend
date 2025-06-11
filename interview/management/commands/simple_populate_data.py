# interview/management/commands/simple_populate_data.py
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Simple data population for testing'

    def handle(self, *args, **options):
        self.stdout.write('Starting simple data population...')
        
        try:
            with transaction.atomic():
                self.create_basic_data()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            return
        
        self.stdout.write(
            self.style.SUCCESS('Successfully populated basic data!')
        )

    def create_basic_data(self):
        """Create minimal data to test the system"""
        
        # 1. Create interview rounds
        from interview.models import InterviewRound
        
        round1, created = InterviewRound.objects.get_or_create(
            name='Phone Screening',
            defaults={
                'description': 'Initial phone screening',
                'sequence_order': 1,
                'typical_duration': 30
            }
        )
        if created:
            self.stdout.write(f"✓ Created interview round: {round1.name}")
        
        # 2. Create candidates
        from candidate.models import Candidate
        
        candidate1, created = Candidate.objects.get_or_create(
            email='john.doe@example.com',
            defaults={
                'name': 'John Doe',
                'phone': '+1234567890',
                'hiring_status': 'applied',
                'current_position': 'Software Engineer',
                'experience_years': 5
            }
        )
        if created:
            self.stdout.write(f"✓ Created candidate: {candidate1.name}")
        
        # 3. Create job and organizational unit
        from mpr.models import Job, OrganizationalUnit
        
        job1, created = Job.objects.get_or_create(
            title='Software Engineer',
            defaults={'description': 'Software Engineer position'}
        )
        if created:
            self.stdout.write(f"✓ Created job: {job1.title}")
        
        dept1, created = OrganizationalUnit.objects.get_or_create(
            name='Engineering',
            type='department',
            defaults={'description': 'Engineering Department', 'code': 'ENG'}
        )
        if created:
            self.stdout.write(f"✓ Created department: {dept1.name}")
        
        # 4. Create location, employment type, etc.
        from mpr.models import Location, EmploymentType, HiringReason, ContractDuration
        
        location1, created = Location.objects.get_or_create(
            name='Main Office',
            defaults={'address': '123 Main St', 'is_active': True}
        )
        if created:
            self.stdout.write(f"✓ Created location: {location1.name}")
        
        emp_type1, created = EmploymentType.objects.get_or_create(
            name='Full Time',
            defaults={'is_active': True}
        )
        if created:
            self.stdout.write(f"✓ Created employment type: {emp_type1.name}")
        
        hiring_reason1, created = HiringReason.objects.get_or_create(
            name='Business Growth',
            defaults={'is_active': True}
        )
        if created:
            self.stdout.write(f"✓ Created hiring reason: {hiring_reason1.name}")
        
        contract_duration1, created = ContractDuration.objects.get_or_create(
            name='Permanent',
            defaults={'duration_months': None, 'is_active': True}
        )
        if created:
            self.stdout.write(f"✓ Created contract duration: {contract_duration1.name}")
        
        # 5. Create MPR
        from mpr.models import MPR
        
        mpr1, created = MPR.objects.get_or_create(
            job_title=job1,
            department=dept1,
            location=location1,
            employment_type=emp_type1,
            hiring_reason=hiring_reason1,
            defaults={
                'priority': 'medium',
                'status': 'approved',
                'education_requirements': 'Bachelor degree in Computer Science',
                'desired_start_date': timezone.now().date(),
                'contract_duration': contract_duration1,
            }
        )
        if created:
            self.stdout.write(f"✓ Created MPR: {mpr1.job_title.title}")
        
        # 6. Create interview
        from interview.models import Interview
        
        interview1, created = Interview.objects.get_or_create(
            candidate=candidate1,
            mpr=mpr1,
            interview_round=round1,
            defaults={
                'scheduled_date': timezone.now() + timedelta(days=1),
                'duration_minutes': 60,
                'status': 'scheduled',
                'interview_type': 'phone',
                'location': 'Phone Call',
            }
        )
        if created:
            self.stdout.write(f"✓ Created interview: {interview1.candidate.name} for {interview1.mpr.job_title.title}")
        
        # 7. Create a user for interviewer
        user1, created = User.objects.get_or_create(
            username='interviewer1',
            defaults={
                'email': 'interviewer1@company.com',
                'first_name': 'Jane',
                'last_name': 'Smith',
            }
        )
        if created:
            self.stdout.write(f"✓ Created user: {user1.username}")
        
        # 8. Create interview participant
        from interview.models import InterviewParticipant
        
        participant1, created = InterviewParticipant.objects.get_or_create(
            interview=interview1,
            user=user1,
            defaults={
                'role': 'primary_interviewer',
                'send_calendar_invite': True,
            }
        )
        if created:
            self.stdout.write(f"✓ Created interview participant: {participant1.user.username}")
        
        # 9. Create interview questions
        from interview.models import InterviewQuestion
        
        question1, created = InterviewQuestion.objects.get_or_create(
            interview_round=round1,
            question_text='Tell me about your experience with Python.',
            defaults={
                'question_type': 'technical',
                'difficulty_level': 'medium',
                'estimated_time_minutes': 10,
                'is_active': True,
            }
        )
        if created:
            self.stdout.write(f"✓ Created interview question: {question1.question_text[:50]}...")
        
        self.stdout.write("\n" + "="*50)
        self.stdout.write("SUMMARY:")
        self.stdout.write(f"Interview Rounds: {InterviewRound.objects.count()}")
        self.stdout.write(f"Candidates: {Candidate.objects.count()}")
        self.stdout.write(f"Jobs: {Job.objects.count()}")
        self.stdout.write(f"MPRs: {MPR.objects.count()}")
        self.stdout.write(f"Interviews: {Interview.objects.count()}")
        self.stdout.write(f"Interview Questions: {InterviewQuestion.objects.count()}")
        self.stdout.write(f"Interview Participants: {InterviewParticipant.objects.count()}")
        self.stdout.write("="*50)