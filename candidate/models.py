# candidate/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import EmailValidator, FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.urls import reverse
import os
import uuid

User = get_user_model()

def candidate_attachment_upload_path(instance, filename):
    """Generate upload path for candidate attachments"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return f"candidates/{instance.candidate.id}/attachments/{filename}"


class Candidate(models.Model):
    """Enhanced Candidate model with CV-like structure"""
    
    # Basic Information
    email = models.EmailField(
        unique=True,
        validators=[EmailValidator()],
        help_text="Primary email address for the candidate"
    )
    name = models.CharField(
        max_length=255,
        help_text="Full name of the candidate"
    )
    
    # Personal Information
    phone = models.CharField(max_length=20, blank=True, null=True)
    alternative_phone = models.CharField(max_length=20, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    nationality = models.CharField(max_length=100, blank=True, null=True)
    
    # Professional Summary
    current_position = models.CharField(max_length=255, blank=True, null=True)
    current_company = models.CharField(max_length=255, blank=True, null=True)
    professional_summary = models.TextField(
        blank=True, 
        help_text="Brief professional summary or objective"
    )
    experience_years = models.PositiveIntegerField(blank=True, null=True)
    
    # Skills and Competencies
    professional_skills = models.JSONField(default=list, blank=True)
    technical_skills = models.JSONField(default=list, blank=True)
    soft_skills = models.JSONField(default=list, blank=True)
    languages = models.JSONField(
        default=list, 
        blank=True,
        help_text="List of languages with proficiency levels"
    )
    certifications = models.JSONField(default=list, blank=True)
    
    # URLs and Links
    linkedin_url = models.URLField(blank=True, null=True)
    portfolio_url = models.URLField(blank=True, null=True)
    github_url = models.URLField(blank=True, null=True)
    personal_website = models.URLField(blank=True, null=True)
    
    # Hiring Information
    HIRING_STATUS_CHOICES = [
        ('applied', 'Applied'),
        ('screening', 'Initial Screening'),
        ('portfolio_review', 'Portfolio Review'),
        ('phone_interview', 'Phone Interview'),
        ('technical_interview', 'Technical Interview'),
        ('final_interview', 'Final Interview'),
        ('reference_check', 'Reference Check'),
        ('offer_pending', 'Offer Pending'),
        ('offer_accepted', 'Offer Accepted'),
        ('offer_declined', 'Offer Declined'),
        ('rejected', 'Rejected'),
        ('on_hold', 'On Hold'),
        ('withdrawn', 'Withdrawn'),
    ]
    
    hiring_status = models.CharField(
        max_length=20,
        choices=HIRING_STATUS_CHOICES,
        default='applied'
    )
    
    # Scores (remove duplication with interview scores)
    overall_score = models.DecimalField(
        max_digits=3, decimal_places=1, blank=True, null=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    skill_match_percentage = models.PositiveIntegerField(
        blank=True, null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    matched_skills_count = models.PositiveIntegerField(blank=True, null=True)
    total_skills_count = models.PositiveIntegerField(blank=True, null=True)
    
    # Salary and Availability
    salary_expectation = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    salary_currency = models.CharField(max_length=3, default='USD', blank=True)
    availability_date = models.DateField(blank=True, null=True)
    notice_period_days = models.PositiveIntegerField(blank=True, null=True)
    
    # Internal Notes
    internal_notes = models.TextField(blank=True)
    
    # Timestamps
    applied_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'candidates'
        ordering = ['-applied_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['hiring_status']),
            models.Index(fields=['applied_at']),
            models.Index(fields=['overall_score']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.email})"
    
    def get_absolute_url(self):
        return reverse('candidate_detail', kwargs={'pk': self.pk})


class CandidateWorkExperience(models.Model):
    """Work experience history for candidates"""
    candidate = models.ForeignKey(
        Candidate, 
        on_delete=models.CASCADE, 
        related_name='work_experiences'
    )
    
    company_name = models.CharField(max_length=255)
    position_title = models.CharField(max_length=255)
    department = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_current = models.BooleanField(default=False)
    
    employment_type = models.CharField(
        max_length=50,
        choices=[
            ('full_time', 'Full Time'),
            ('part_time', 'Part Time'),
            ('contract', 'Contract'),
            ('freelance', 'Freelance'),
            ('internship', 'Internship'),
            ('volunteer', 'Volunteer'),
        ],
        default='full_time'
    )
    
    job_description = models.TextField(blank=True)
    key_achievements = models.TextField(blank=True)
    technologies_used = models.JSONField(default=list, blank=True)
    
    # Order for display
    display_order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'candidate_work_experiences'
        ordering = ['-start_date', 'display_order']
    
    def __str__(self):
        return f"{self.candidate.name} - {self.position_title} at {self.company_name}"


class CandidateEducation(models.Model):
    """Education history for candidates"""
    candidate = models.ForeignKey(
        Candidate, 
        on_delete=models.CASCADE, 
        related_name='education_history'
    )
    
    institution_name = models.CharField(max_length=255)
    degree_type = models.CharField(
        max_length=50,
        choices=[
            ('high_school', 'High School'),
            ('diploma', 'Diploma'),
            ('associate', 'Associate Degree'),
            ('bachelor', 'Bachelor Degree'),
            ('master', 'Master Degree'),
            ('phd', 'PhD'),
            ('professional', 'Professional Certificate'),
            ('other', 'Other'),
        ]
    )
    field_of_study = models.CharField(max_length=255)
    specialization = models.CharField(max_length=255, blank=True)
    
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_current = models.BooleanField(default=False)
    
    grade_gpa = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=255, blank=True)
    
    # Additional details
    thesis_title = models.CharField(max_length=500, blank=True)
    honors_awards = models.TextField(blank=True)
    relevant_coursework = models.TextField(blank=True)
    
    # Order for display
    display_order = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'candidate_education'
        ordering = ['-start_date', 'display_order']
    
    def __str__(self):
        return f"{self.candidate.name} - {self.degree_type} in {self.field_of_study}"


class CandidateProject(models.Model):
    """Projects and portfolio items for candidates"""
    candidate = models.ForeignKey(
        Candidate, 
        on_delete=models.CASCADE, 
        related_name='projects'
    )
    
    project_name = models.CharField(max_length=255)
    project_type = models.CharField(
        max_length=50,
        choices=[
            ('professional', 'Professional Project'),
            ('personal', 'Personal Project'),
            ('academic', 'Academic Project'),
            ('open_source', 'Open Source'),
            ('freelance', 'Freelance Project'),
        ],
        default='professional'
    )
    
    description = models.TextField()
    technologies_used = models.JSONField(default=list, blank=True)
    
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    
    project_url = models.URLField(blank=True, null=True)
    github_url = models.URLField(blank=True, null=True)
    demo_url = models.URLField(blank=True, null=True)
    
    # Order for display
    display_order = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'candidate_projects'
        ordering = ['-is_featured', '-start_date', 'display_order']
    
    def __str__(self):
        return f"{self.candidate.name} - {self.project_name}"


class CandidateReference(models.Model):
    """Professional references for candidates"""
    candidate = models.ForeignKey(
        Candidate, 
        on_delete=models.CASCADE, 
        related_name='references'
    )
    
    reference_name = models.CharField(max_length=255)
    reference_title = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255)
    relationship = models.CharField(
        max_length=100,
        choices=[
            ('supervisor', 'Direct Supervisor'),
            ('manager', 'Manager'),
            ('colleague', 'Colleague'),
            ('client', 'Client'),
            ('mentor', 'Mentor'),
            ('other', 'Other'),
        ]
    )
    
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    
    permission_to_contact = models.BooleanField(default=False)
    contact_preference = models.CharField(
        max_length=20,
        choices=[
            ('email', 'Email'),
            ('phone', 'Phone'),
            ('both', 'Both'),
        ],
        default='email'
    )
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'candidate_references'
        ordering = ['reference_name']
    
    def __str__(self):
        return f"{self.candidate.name} - {self.reference_name}"


# REMOVED DUPLICATE EMAIL MODELS - Using email_service instead
class CandidateEmailConnection(models.Model):
    """Connection between candidates and email_service messages"""
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name='email_connections'
    )
    
    # Connection to email_service.EmailMessage
    email_message = models.ForeignKey(
        'email_service.EmailMessage',
        on_delete=models.CASCADE,
        related_name='candidate_connections'
    )
    
    # Email categorization for candidate context
    email_type = models.CharField(
        max_length=50,
        choices=[
            ('application', 'Application Email'),
            ('follow_up', 'Follow-up Email'),
            ('interview_invitation', 'Interview Invitation'),
            ('interview_confirmation', 'Interview Confirmation'),
            ('interview_reminder', 'Interview Reminder'),
            ('feedback_request', 'Feedback Request'),
            ('offer_letter', 'Offer Letter'),
            ('rejection_letter', 'Rejection Letter'),
            ('general', 'General Communication'),
        ],
        default='general'
    )
    
    # Candidate-specific metadata
    is_inbound = models.BooleanField(
        default=True,
        help_text="True if email is from candidate to us"
    )
    
    # Workflow tracking
    requires_response = models.BooleanField(default=False)
    is_responded = models.BooleanField(default=False)
    
    # Internal notes about this email in candidate context
    internal_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'candidate_email_connections'
        unique_together = ['candidate', 'email_message']
        ordering = ['-email_message__received_datetime']
    
    def __str__(self):
        return f"{self.candidate.name} - {self.email_message.subject}"


class CandidateAttachment(models.Model):
    """File attachments for candidates (CV, portfolios, etc.)"""
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    
    # Connection to email attachment if it came from email
    email_connection = models.ForeignKey(
        CandidateEmailConnection,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='attachments'
    )
    
    # File information
    file_name = models.CharField(max_length=255)
    original_file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    
    file_type = models.CharField(
        max_length=50,
        choices=[
            ('cv', 'CV/Resume'),
            ('cover_letter', 'Cover Letter'),
            ('portfolio', 'Portfolio'),
            ('certificate', 'Certificate'),
            ('transcript', 'Transcript'),
            ('photo', 'Photo'),
            ('project_file', 'Project File'),
            ('other', 'Other Document'),
        ],
        default='other'
    )
    
    mime_type = models.CharField(max_length=100)
    
    # File storage
    file = models.FileField(
        upload_to=candidate_attachment_upload_path,
        validators=[FileExtensionValidator(
            allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'zip', 'rar']
        )]
    )
    
    # CV/Resume specific flags
    is_primary_cv = models.BooleanField(default=False)
    is_latest_version = models.BooleanField(default=True)
    
    # Processing status
    is_processed = models.BooleanField(default=False)
    processing_notes = models.TextField(blank=True)
    
    # Metadata
    description = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_candidate_attachments'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'candidate_attachments'
        ordering = ['-is_primary_cv', '-created_at']
        indexes = [
            models.Index(fields=['candidate', 'file_type']),
            models.Index(fields=['is_primary_cv']),
        ]
    
    def __str__(self):
        return f"{self.candidate.name} - {self.file_name}"


class CandidateStatusUpdate(models.Model):
    """Track status changes for candidates"""
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name='status_updates'
    )
    
    previous_status = models.CharField(
        max_length=20,
        choices=Candidate.HIRING_STATUS_CHOICES,
        null=True,
        blank=True
        
    )
    new_status = models.CharField(
        max_length=20,
        choices=Candidate.HIRING_STATUS_CHOICES,
        null=True,
        blank=True
    )
    
    reason = models.TextField(blank=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='candidate_status_updates'
    )
    updated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'candidate_status_updates'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.candidate.name}: {self.previous_status} → {self.new_status}"


# Connection model to MPR applications
class CandidateMPR(models.Model):
    """Many-to-many relationship between candidates and MPRs with additional data"""
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name='mpr_applications'
    )
    mpr = models.ForeignKey(
        'mpr.MPR',
        on_delete=models.CASCADE,
        related_name='candidate_applications'
    )
    
    # Application specific information
    application_stage = models.CharField(
        max_length=30,
        choices=[
            ('applied', 'Applied'),
            ('under_review', 'Under Review'),
            ('shortlisted', 'Shortlisted'),
            ('interview_scheduled', 'Interview Scheduled'),
            ('interviewed', 'Interviewed'),
            ('final_review', 'Final Review'),
            ('offer_made', 'Offer Made'),
            ('hired', 'Hired'),
            ('rejected', 'Rejected'),
            ('withdrawn', 'Withdrawn'),
        ],
        default='applied'
    )
    
    # CV used for this application
    primary_cv = models.ForeignKey(
        CandidateAttachment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mpr_applications_as_cv'
    )
    
    # Application specific scores and notes
    application_notes = models.TextField(blank=True)
    recruiter_notes = models.TextField(blank=True)
    
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_candidate_mprs'
    )
    
    class Meta:
        db_table = 'candidate_mpr_applications'
        unique_together = ['candidate', 'mpr']
        ordering = ['-applied_at']
    
    def __str__(self):
        return f"{self.candidate.name} applied to {self.mpr.mpr_number}"