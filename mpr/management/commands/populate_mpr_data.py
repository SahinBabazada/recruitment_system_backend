# mpr/management/__init__.py
# Empty file

# mpr/management/commands/__init__.py
# Empty file

# mpr/management/commands/populate_mpr_data.py
from django.core.management.base import BaseCommand
from django.db import transaction
from mpr.models import (
    Job, OrganizationalUnit, Location, EmploymentType, HiringReason,
    TechnicalSkill, Language, Competency, ContractDuration
)


class Command(BaseCommand):
    help = 'Populate MPR system with default data'

    def handle(self, *args, **options):
        self.stdout.write('Starting to populate MPR data...')
        
        with transaction.atomic():
            self.create_employment_types()
            self.create_hiring_reasons()
            self.create_contract_durations()
            self.create_languages()
            self.create_organizational_units()
            self.create_locations()
            self.create_jobs()
            self.create_technical_skills()
            self.create_competencies()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully populated MPR data!')
        )

    def create_employment_types(self):
        """Create default employment types"""
        employment_types = [
            {'name': 'Replacement for', 'description': 'Replacing an existing employee', 'is_default': True},
            {'name': 'New Position', 'description': 'Creating a new position', 'is_default': True},
            {'name': 'Budgeted Headcount', 'description': 'Planned headcount increase', 'is_default': True},
            {'name': 'Permanent', 'description': 'Permanent employment'},
            {'name': 'Temporary', 'description': 'Temporary employment'},
            {'name': 'Contract', 'description': 'Contract-based employment'},
            {'name': 'Internship', 'description': 'Internship position'},
            {'name': 'Part-time', 'description': 'Part-time employment'},
        ]
        
        for et_data in employment_types:
            et, created = EmploymentType.objects.get_or_create(
                name=et_data['name'],
                defaults=et_data
            )
            if created:
                self.stdout.write(f"Created employment type: {et.name}")

    def create_hiring_reasons(self):
        """Create default hiring reasons"""
        hiring_reasons = [
            {'name': 'Business Growth', 'description': 'Expanding business operations', 'is_default': True},
            {'name': 'Replacement', 'description': 'Replacing departing employee', 'is_default': True},
            {'name': 'New Project', 'description': 'Starting new project or initiative', 'is_default': True},
            {'name': 'Seasonal', 'description': 'Seasonal workforce increase', 'is_default': True},
            {'name': 'Restructuring', 'description': 'Organizational restructuring', 'is_default': True},
            {'name': 'Skills Gap', 'description': 'Filling critical skills gap'},
            {'name': 'Workload Increase', 'description': 'Increased workload'},
            {'name': 'New Department', 'description': 'Creating new department'},
            {'name': 'Compliance Requirement', 'description': 'Regulatory or compliance needs'},
            {'name': 'Technology Implementation', 'description': 'New technology implementation'},
        ]
        
        for hr_data in hiring_reasons:
            hr, created = HiringReason.objects.get_or_create(
                name=hr_data['name'],
                defaults=hr_data
            )
            if created:
                self.stdout.write(f"Created hiring reason: {hr.name}")

    def create_contract_durations(self):
        """Create default contract durations"""
        durations = [
            {'name': 'Permanent', 'months': None, 'description': 'Permanent employment', 'is_default': True},
            {'name': '1 Year', 'months': 12, 'description': '12-month contract'},
            {'name': '2 Years', 'months': 24, 'description': '24-month contract'},
            {'name': '6 Months', 'months': 6, 'description': '6-month contract'},
            {'name': '3 Months', 'months': 3, 'description': '3-month contract'},
            {'name': 'Project-based', 'months': None, 'description': 'Duration based on project timeline'},
        ]
        
        for duration_data in durations:
            duration, created = ContractDuration.objects.get_or_create(
                name=duration_data['name'],
                defaults=duration_data
            )
            if created:
                self.stdout.write(f"Created contract duration: {duration.name}")

    def create_languages(self):
        """Create default languages"""
        languages = [
            {'name': 'English', 'code': 'en'},
            {'name': 'Azerbaijani', 'code': 'az'},
            {'name': 'Turkish', 'code': 'tr'},
            {'name': 'Russian', 'code': 'ru'},
            {'name': 'French', 'code': 'fr'},
            {'name': 'German', 'code': 'de'},
            {'name': 'Spanish', 'code': 'es'},
            {'name': 'Arabic', 'code': 'ar'},
            {'name': 'Persian', 'code': 'fa'},
            {'name': 'Chinese', 'code': 'zh'},
        ]
        
        for lang_data in languages:
            lang, created = Language.objects.get_or_create(
                code=lang_data['code'],
                defaults=lang_data
            )
            if created:
                self.stdout.write(f"Created language: {lang.name}")

    def create_organizational_units(self):
        """Create default organizational structure"""
        # Departments
        departments = [
            {'name': 'Engineering', 'code': 'ENG'},
            {'name': 'Marketing', 'code': 'MKT'},
            {'name': 'Sales', 'code': 'SAL'},
            {'name': 'Human Resources', 'code': 'HR'},
            {'name': 'Finance', 'code': 'FIN'},
            {'name': 'Operations', 'code': 'OPS'},
            {'name': 'IT Support', 'code': 'IT'},
            {'name': 'Legal', 'code': 'LEG'},
            {'name': 'Quality Assurance', 'code': 'QA'},
            {'name': 'Research & Development', 'code': 'RND'},
        ]
        
        created_departments = {}
        for dept_data in departments:
            dept, created = OrganizationalUnit.objects.get_or_create(
                name=dept_data['name'],
                type='department',
                defaults={
                    'code': dept_data['code'],
                    'description': f"{dept_data['name']} Department"
                }
            )
            created_departments[dept.name] = dept
            if created:
                self.stdout.write(f"Created department: {dept.name}")

        # Divisions and Units for Engineering
        if 'Engineering' in created_departments:
            eng_dept = created_departments['Engineering']
            
            # Engineering Divisions
            eng_divisions = [
                {'name': 'Software Development', 'code': 'ENG-SD'},
                {'name': 'Data Engineering', 'code': 'ENG-DE'},
                {'name': 'DevOps', 'code': 'ENG-DO'},
            ]
            
            for div_data in eng_divisions:
                div, created = OrganizationalUnit.objects.get_or_create(
                    name=div_data['name'],
                    type='division',
                    parent=eng_dept,
                    defaults={
                        'code': div_data['code'],
                        'description': f"{div_data['name']} Division"
                    }
                )
                if created:
                    self.stdout.write(f"Created division: {div.name}")

    def create_locations(self):
        """Create default locations"""
        locations = [
            {
                'name': 'Baku Office',
                'address': 'Main Office, Baku, Azerbaijan',
                'city': 'Baku',
                'country': 'Azerbaijan',
                'location_type': 'office'
            },
            {
                'name': 'Remote',
                'address': '',
                'city': '',
                'country': '',
                'location_type': 'remote'
            },
            {
                'name': 'Hybrid',
                'address': 'Flexible location',
                'city': '',
                'country': '',
                'location_type': 'hybrid'
            },
            {
                'name': 'Client Site',
                'address': 'Various client locations',
                'city': '',
                'country': '',
                'location_type': 'client_site'
            },
            {
                'name': 'Ganja Office',
                'address': 'Branch Office, Ganja, Azerbaijan',
                'city': 'Ganja',
                'country': 'Azerbaijan',
                'location_type': 'office'
            },
        ]
        
        for loc_data in locations:
            loc, created = Location.objects.get_or_create(
                name=loc_data['name'],
                defaults=loc_data
            )
            if created:
                self.stdout.write(f"Created location: {loc.name}")

    def create_jobs(self):
        """Create default job titles"""
        jobs = [
            'Software Engineer',
            'Senior Software Engineer',
            'Lead Software Engineer',
            'Frontend Developer',
            'Backend Developer',
            'Full Stack Developer',
            'DevOps Engineer',
            'Data Engineer',
            'Data Scientist',
            'Product Manager',
            'Project Manager',
            'Business Analyst',
            'UI/UX Designer',
            'Quality Assurance Engineer',
            'Marketing Manager',
            'Sales Representative',
            'Account Manager',
            'HR Specialist',
            'HR Manager',
            'Financial Analyst',
            'Operations Manager',
            'IT Support Specialist',
            'System Administrator',
            'Network Administrator',
            'Security Specialist',
            'Content Writer',
            'Digital Marketing Specialist',
            'Customer Success Manager',
            'Technical Writer',
            'Research Analyst',
        ]
        
        for job_title in jobs:
            job, created = Job.objects.get_or_create(
                title=job_title,
                defaults={'description': f'{job_title} position'}
            )
            if created:
                self.stdout.write(f"Created job: {job.title}")

    def create_technical_skills(self):
        """Create default technical skills"""
        skills_by_category = {
            'Programming Languages': [
                'Python', 'JavaScript', 'Java', 'C#', 'C++', 'Go', 'Rust',
                'TypeScript', 'PHP', 'Ruby', 'Swift', 'Kotlin', 'Scala'
            ],
            'Web Technologies': [
                'React', 'Angular', 'Vue.js', 'Node.js', 'Express.js',
                'Django', 'Flask', 'ASP.NET', 'Spring Boot', 'Laravel'
            ],
            'Databases': [
                'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Elasticsearch',
                'Oracle', 'SQL Server', 'SQLite', 'Cassandra', 'DynamoDB'
            ],
            'Cloud Platforms': [
                'AWS', 'Azure', 'Google Cloud', 'Kubernetes', 'Docker',
                'Terraform', 'Ansible', 'Jenkins', 'GitLab CI/CD', 'CircleCI'
            ],
            'Data & Analytics': [
                'Machine Learning', 'Deep Learning', 'Data Analysis',
                'Pandas', 'NumPy', 'TensorFlow', 'PyTorch', 'Tableau', 'Power BI'
            ],
            'Mobile Development': [
                'React Native', 'Flutter', 'iOS Development', 'Android Development',
                'Xamarin', 'Ionic', 'Cordova'
            ],
            'DevOps & Tools': [
                'Git', 'GitHub', 'GitLab', 'JIRA', 'Confluence',
                'Linux', 'Windows Server', 'Bash', 'PowerShell'
            ],
            'Testing': [
                'Unit Testing', 'Integration Testing', 'Selenium',
                'Jest', 'Pytest', 'Cypress', 'Postman', 'JMeter'
            ]
        }
        
        for category, skills in skills_by_category.items():
            for skill_name in skills:
                skill, created = TechnicalSkill.objects.get_or_create(
                    name=skill_name,
                    defaults={
                        'category': category,
                        'description': f'{skill_name} technical skill'
                    }
                )
                if created:
                    self.stdout.write(f"Created technical skill: {skill.name}")

    def create_competencies(self):
        """Create default competencies"""
        competencies_by_category = {
            'Leadership': [
                'Team Leadership', 'Strategic Thinking', 'Decision Making',
                'Conflict Resolution', 'Mentoring', 'Vision Setting',
                'Change Management', 'Delegation'
            ],
            'Communication': [
                'Verbal Communication', 'Written Communication', 'Presentation Skills',
                'Active Listening', 'Negotiation', 'Public Speaking',
                'Cross-cultural Communication', 'Technical Writing'
            ],
            'Technical': [
                'Problem Solving', 'Analytical Thinking', 'System Design',
                'Code Review', 'Architecture Design', 'Performance Optimization',
                'Security Awareness', 'Quality Assurance'
            ],
            'Behavioral': [
                'Teamwork', 'Adaptability', 'Time Management', 'Self-motivation',
                'Creativity', 'Initiative', 'Reliability', 'Attention to Detail',
                'Customer Focus', 'Continuous Learning'
            ],
            'Project Management': [
                'Agile Methodology', 'Scrum', 'Kanban', 'Risk Management',
                'Resource Planning', 'Budget Management', 'Stakeholder Management',
                'Process Improvement'
            ],
            'Business': [
                'Business Analysis', 'Market Research', 'Financial Analysis',
                'Sales Skills', 'Customer Relationship Management',
                'Product Management', 'Strategy Development'
            ]
        }
        
        for category, competencies in competencies_by_category.items():
            for comp_name in competencies:
                comp, created = Competency.objects.get_or_create(
                    name=comp_name,
                    defaults={
                        'category': category,
                        'description': f'{comp_name} competency'
                    }
                )
                if created:
                    self.stdout.write(f"Created competency: {comp.name}")

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before populating',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            with transaction.atomic():
                # Clear in reverse dependency order
                TechnicalSkill.objects.all().delete()
                Competency.objects.all().delete()
                Job.objects.all().delete()
                Location.objects.all().delete()
                OrganizationalUnit.objects.all().delete()
                Language.objects.all().delete()
                ContractDuration.objects.all().delete()
                HiringReason.objects.all().delete()
                EmploymentType.objects.all().delete()
            self.stdout.write(self.style.WARNING('Existing data cleared!'))
        
        self.stdout.write('Starting to populate MPR data...')
        
        with transaction.atomic():
            self.create_employment_types()
            self.create_hiring_reasons()
            self.create_contract_durations()
            self.create_languages()
            self.create_organizational_units()
            self.create_locations()
            self.create_jobs()
            self.create_technical_skills()
            self.create_competencies()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully populated MPR data!')
        )