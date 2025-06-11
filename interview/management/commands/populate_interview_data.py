# interview/management/commands/populate_interview_data.py
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate interview system with sample data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--candidates',
            type=int,
            default=20,
            help='Number of candidates to create (default: 20)',
        )
        parser.add_argument(
            '--interviews',
            type=int,
            default=30,
            help='Number of interviews to create (default: 30)',
        )
        parser.add_argument(
            '--questions',
            type=int,
            default=50,
            help='Number of interview questions to create (default: 50)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing interview data before populating',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.clear_existing_data()
        
        self.stdout.write('Starting to populate interview data...')
        
        try:
            with transaction.atomic():
                # First ensure we have a user for created_by fields
                admin_user = self.get_or_create_admin_user()
                
                # Create interview rounds first
                interview_rounds = self.create_interview_rounds()
                
                # Create sample candidates
                candidates = self.create_candidates(options['candidates'])
                
                # Create sample MPRs
                mprs = self.create_mprs(admin_user)
                
                # Create interview questions
                questions = self.create_interview_questions(
                    options['questions'], 
                    interview_rounds,
                    admin_user
                )
                
                # Create interviews
                interviews = self.create_interviews(
                    options['interviews'], 
                    candidates, 
                    mprs, 
                    interview_rounds,
                    admin_user
                )
                
                # Create interview participants
                self.create_interview_participants(interviews, admin_user)
                
                # Create some question responses
                self.create_question_responses(interviews, questions)
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error occurred: {str(e)}'))
            raise
        
        self.stdout.write(
            self.style.SUCCESS('Successfully populated interview data!')
        )

    def clear_existing_data(self):
        """Clear existing interview data"""
        self.stdout.write('Clearing existing interview data...')
        
        from interview.models import (
            InterviewQuestionResponse, InterviewParticipant, Interview, 
            InterviewQuestion, InterviewRound
        )
        
        InterviewQuestionResponse.objects.all().delete()
        InterviewParticipant.objects.all().delete()
        Interview.objects.all().delete()
        InterviewQuestion.objects.all().delete()
        InterviewRound.objects.all().delete()
        
        self.stdout.write(self.style.WARNING('Existing interview data cleared!'))

    def get_or_create_admin_user(self):
        """Get or create an admin user for created_by fields"""
        admin_user, created = User.objects.get_or_create(
            username='system_admin',
            defaults={
                'email': 'admin@company.com',
                'first_name': 'System',
                'last_name': 'Admin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(f"✓ Created admin user: {admin_user.username}")
        
        return admin_user

    def create_interview_rounds(self):
        """Create interview rounds"""
        from interview.models import InterviewRound
        
        rounds_data = [
            {'name': 'Phone Screening', 'sequence_order': 1, 'description': 'Initial phone screening with HR'},
            {'name': 'Technical Round 1', 'sequence_order': 2, 'description': 'Basic technical assessment'},
            {'name': 'Technical Round 2', 'sequence_order': 3, 'description': 'Advanced technical interview'},
            {'name': 'Behavioral', 'sequence_order': 4, 'description': 'Behavioral and cultural fit assessment'},
            {'name': 'Final Round', 'sequence_order': 5, 'description': 'Final interview with leadership'},
        ]
        
        rounds = []
        for round_data in rounds_data:
            round_obj, created = InterviewRound.objects.get_or_create(
                name=round_data['name'],
                defaults=round_data
            )
            rounds.append(round_obj)
            if created:
                self.stdout.write(f"✓ Created interview round: {round_obj.name}")
        
        return rounds

    def create_candidates(self, count):
        """Create sample candidates"""
        from candidate.models import Candidate
        
        first_names = [
            'Alice', 'Bob', 'Charlie', 'Diana', 'Edward', 'Fiona', 'George', 'Helen',
            'Ivan', 'Julia', 'Kevin', 'Lisa', 'Michael', 'Nancy', 'Oliver', 'Petra',
            'Quinn', 'Rachel', 'Steve', 'Tina', 'Uma', 'Victor', 'Wendy', 'Xavier',
            'Yvonne', 'Zachary'
        ]
        
        last_names = [
            'Anderson', 'Brown', 'Davis', 'Garcia', 'Johnson', 'Jones', 'Miller',
            'Rodriguez', 'Smith', 'Taylor', 'Williams', 'Wilson'
        ]
        
        positions = [
            'Software Engineer', 'Senior Software Engineer', 'Data Scientist',
            'Product Manager', 'Frontend Developer', 'Backend Developer',
            'Full Stack Developer', 'DevOps Engineer', 'QA Engineer'
        ]
        
        companies = [
            'Tech Corp', 'Innovation Labs', 'Digital Solutions', 'Future Systems',
            'Smart Technologies', 'Data Dynamics', 'Cloud First', 'Agile Works'
        ]
        
        candidates = []
        for i in range(count):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            full_name = f"{first_name} {last_name}"
            
            candidate, created = Candidate.objects.get_or_create(
                email=f"{first_name.lower()}.{last_name.lower()}{i}@example.com",
                defaults={
                    'name': full_name,
                    'phone': f"+1{random.randint(1000000000, 9999999999)}",
                    'hiring_status': random.choice(['applied', 'screening', 'interviewing', 'offered', 'hired', 'rejected']),
                    'current_position': random.choice(positions),
                    'current_company': random.choice(companies),
                    'experience_years': random.randint(1, 15),
                    'location': random.choice(['New York', 'San Francisco', 'Seattle', 'Austin', 'Remote']),
                    'technical_skills': random.sample(['Python', 'JavaScript', 'React', 'Django', 'AWS', 'Docker', 'SQL'], 3),
                    'professional_summary': f'Experienced {random.choice(positions).lower()} with {random.randint(2, 10)} years of experience.',
                }
            )
            candidates.append(candidate)
            if created:
                self.stdout.write(f"✓ Created candidate: {candidate.name}")
        
        return candidates

    def create_mprs(self, admin_user):
        """Create sample MPRs with proper user context"""
        from mpr.models import (
            MPR, Job, OrganizationalUnit, Location, EmploymentType, 
            HiringReason, ContractDuration
        )
        
        # Create jobs
        job_titles = ['Software Engineer', 'Data Scientist', 'Product Manager', 'DevOps Engineer']
        jobs = []
        
        for title in job_titles:
            job, created = Job.objects.get_or_create(
                title=title,
                defaults={
                    'description': f'{title} position',
                    'created_by': admin_user
                }
            )
            jobs.append(job)
            if created:
                self.stdout.write(f"✓ Created job: {job.title}")
        
        # Create organizational unit (department)
        dept, created = OrganizationalUnit.objects.get_or_create(
            name='Engineering',
            type='department',
            defaults={
                'description': 'Engineering Department', 
                'code': 'ENG',
                'created_by': admin_user
            }
        )
        if created:
            self.stdout.write(f"✓ Created department: {dept.name}")
        
        # Create location
        location, created = Location.objects.get_or_create(
            name='Main Office',
            defaults={
                'address': '123 Main St', 
                'is_active': True
            }
        )
        if created:
            self.stdout.write(f"✓ Created location: {location.name}")
        
        # Create employment type
        employment_type, created = EmploymentType.objects.get_or_create(
            name='Full Time',
            defaults={'is_active': True}
        )
        if created:
            self.stdout.write(f"✓ Created employment type: {employment_type.name}")
        
        # Create hiring reason
        hiring_reason, created = HiringReason.objects.get_or_create(
            name='Business Growth',
            defaults={'is_active': True}
        )
        if created:
            self.stdout.write(f"✓ Created hiring reason: {hiring_reason.name}")
        
        # Create contract duration
        contract_duration, created = ContractDuration.objects.get_or_create(
            name='Permanent',
            defaults={'months': None, 'is_active': True}
        )
        if created:
            self.stdout.write(f"✓ Created contract duration: {contract_duration.name}")
        
        # Create MPRs
        mprs = []
        for i, job in enumerate(jobs):
            mpr, created = MPR.objects.get_or_create(
                job_title=job,
                department=dept,
                location=location,
                employment_type=employment_type,
                hiring_reason=hiring_reason,
                contract_duration=contract_duration,
                created_by=admin_user,  # IMPORTANT: Required field
                defaults={
                    'priority': random.choice(['low', 'medium', 'high', 'urgent']),
                    'status': random.choice(['draft', 'pending', 'approved', 'published']),
                    'education_requirements': f'Requirements for {job.title} position',
                    'desired_start_date': timezone.now().date(),
                }
            )
            mprs.append(mpr)
            if created:
                self.stdout.write(f"✓ Created MPR: {mpr.job_title.title}")
        
        return mprs

    def create_interview_questions(self, count, interview_rounds, admin_user):
        """Create sample interview questions"""
        from interview.models import InterviewQuestion
        
        question_templates = {
            'technical': [
                "Explain the difference between lists and dictionaries in Python",
                "How would you optimize a database query?",
                "What are the advantages of using microservices?",
                "Implement a binary search algorithm",
                "Describe the architecture of a REST API",
                "What is the difference between SQL and NoSQL databases?",
                "How do you handle errors in your code?",
                "Explain object-oriented programming concepts",
            ],
            'behavioral': [
                "Tell me about a time when you had to resolve conflicts",
                "How do you handle working under pressure?",
                "Describe a challenging project you faced",
                "What motivates you in your work?",
                "How do you prioritize tasks when everything is urgent?",
                "Tell me about a time you made a mistake",
                "How do you stay updated with new technologies?",
                "Describe your ideal work environment",
            ],
            'cultural': [
                "How do you work in a team environment?",
                "What interests you about our company?",
                "How do you handle feedback and criticism?",
                "What are your long-term career goals?",
                "How do you approach learning new skills?",
                "What do you do when you disagree with your manager?",
                "How do you handle work-life balance?",
                "What type of work environment helps you thrive?",
            ]
        }
        
        questions = []
        for i in range(count):
            question_type = random.choice(['technical', 'behavioral', 'cultural'])
            question_text = random.choice(question_templates[question_type])
            
            question, created = InterviewQuestion.objects.get_or_create(
                question_text=question_text,
                interview_round=random.choice(interview_rounds),
                defaults={
                    'question_type': question_type,
                    'difficulty_level': random.choice(['easy', 'medium', 'hard']),
                    'estimated_time_minutes': random.randint(5, 30),
                    'is_active': True,
                    'usage_count': random.randint(0, 10),
                    'created_by': admin_user,
                }
            )
            questions.append(question)
            if created:
                self.stdout.write(f"✓ Created question: {question_text[:50]}...")
        
        return questions

    def create_interviews(self, count, candidates, mprs, interview_rounds, admin_user):
        """Create sample interviews"""
        from interview.models import Interview
        
        interviews = []
        
        for i in range(count):
            # Random date in the past 30 days or future 30 days
            days_offset = random.randint(-30, 30)
            scheduled_date = timezone.now() + timedelta(days=days_offset)
            
            interview, created = Interview.objects.get_or_create(
                candidate=random.choice(candidates),
                mpr=random.choice(mprs),
                interview_round=random.choice(interview_rounds),
                defaults={
                    'scheduled_date': scheduled_date,
                    'duration_minutes': random.choice([30, 45, 60, 90]),
                    'status': random.choice(['scheduled', 'confirmed', 'in_progress', 'completed', 'cancelled']),
                    'location': random.choice(['Conference Room A', 'Conference Room B', 'Online', 'Phone']),
                    'meeting_link': 'https://meet.google.com/abc-def-ghi' if random.choice([True, False]) else None,
                    'meeting_details': f'Meeting details for interview {i+1}',
                    'interviewer_notes': f'Interview notes for candidate {i+1}',
                    'preparation_notes': f'Preparation notes for interview {i+1}',
                    'overall_score': random.uniform(1.0, 5.0) if random.choice([True, False]) else None,
                    'created_by': admin_user,
                }
            )
            interviews.append(interview)
            if created:
                self.stdout.write(f"✓ Created interview: {interview.candidate.name} for {interview.mpr.job_title.title}")
        
        return interviews

    def create_interview_participants(self, interviews, admin_user):
        """Create interview participants"""
        from interview.models import InterviewParticipant
        
        # Create some users to act as interviewers
        users = []
        for i in range(5):
            user, created = User.objects.get_or_create(
                username=f'interviewer{i+1}',
                defaults={
                    'email': f'interviewer{i+1}@company.com',
                    'first_name': f'Interviewer{i+1}',
                    'last_name': f'User',
                }
            )
            users.append(user)
            if created:
                self.stdout.write(f"✓ Created interviewer: {user.username}")
        
        # Add admin_user to the list
        users.append(admin_user)
        
        for interview in interviews:
            # Add 1-3 participants per interview
            num_participants = random.randint(1, 3)
            selected_users = random.sample(users, min(num_participants, len(users)))
            
            for j, user in enumerate(selected_users):
                role = 'primary_interviewer' if j == 0 else random.choice([
                    'technical_interviewer', 'behavioral_interviewer', 'observer'
                ])
                
                participant, created = InterviewParticipant.objects.get_or_create(
                    interview=interview,
                    user=user,
                    defaults={
                        'role': role,
                        'individual_score': random.uniform(1.0, 5.0) if random.choice([True, False]) else None,
                        'individual_feedback': f'Feedback from {user.first_name}' if random.choice([True, False]) else '',
                        'individual_recommendation': random.choice(['hire', 'no_hire', 'maybe']) if random.choice([True, False]) else None,
                    }
                )
                if created:
                    self.stdout.write(f"✓ Added participant: {user.username} to interview")

    def create_question_responses(self, interviews, questions):
        """Create sample question responses"""
        from interview.models import InterviewQuestionResponse
        
        completed_interviews = [i for i in interviews if i.status == 'completed']
        
        for interview in completed_interviews[:10]:  # Only for first 10 completed interviews
            # Check if interview has participants
            participants = interview.participants.all()
            if not participants:
                continue
                
            # Add 3-8 questions per interview
            num_questions = random.randint(3, 8)
            selected_questions = random.sample(questions, min(num_questions, len(questions)))
            
            for question in selected_questions:
                # Select a random participant who asked the question
                asked_by_participant = random.choice(participants)
                
                response, created = InterviewQuestionResponse.objects.get_or_create(
                    interview=interview,
                    question=question,
                    asked_by=asked_by_participant,
                    defaults={
                        'candidate_answer': f'Sample response to: {question.question_text[:30]}...',
                        'interviewer_notes': f'Notes about the response to question {question.id}',
                        'response_score': random.uniform(1.0, 5.0),
                        'time_taken_minutes': random.randint(2, 15),
                    }
                )
                if created:
                    self.stdout.write(f"✓ Created question response for interview {interview.id}")
        
        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print summary of created data"""
        from interview.models import (
            InterviewRound, Interview, InterviewParticipant, 
            InterviewQuestion, InterviewQuestionResponse
        )
        from candidate.models import Candidate
        from mpr.models import MPR, Job
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("DATA POPULATION SUMMARY"))
        self.stdout.write("="*60)
        self.stdout.write(f"Interview Rounds: {InterviewRound.objects.count()}")
        self.stdout.write(f"Candidates: {Candidate.objects.count()}")
        self.stdout.write(f"Jobs: {Job.objects.count()}")
        self.stdout.write(f"MPRs: {MPR.objects.count()}")
        self.stdout.write(f"Interviews: {Interview.objects.count()}")
        self.stdout.write(f"Interview Questions: {InterviewQuestion.objects.count()}")
        self.stdout.write(f"Interview Participants: {InterviewParticipant.objects.count()}")
        self.stdout.write(f"Question Responses: {InterviewQuestionResponse.objects.count()}")
        self.stdout.write(f"Users: {User.objects.count()}")
        self.stdout.write("="*60)