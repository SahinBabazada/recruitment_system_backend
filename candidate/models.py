from django.db import models
from django.contrib.auth.models import User
from django.core.validators import EmailValidator, FileExtensionValidator
from django.urls import reverse
import os
import uuid
from django.contrib.auth import get_user_model

User = get_user_model()

from django.conf import settings

def candidate_attachment_upload_path(instance, filename):
    """Generate upload path for candidate attachments"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return f"candidates/{instance.candidate.id}/attachments/{filename}"


class Candidate(models.Model):
    """Candidate model based on the provided image"""
    
    # Required fields
    email = models.EmailField(
        unique=True,
        validators=[EmailValidator()],
        help_text="Primary email address for the candidate"
    )
    name = models.CharField(
        max_length=255,
        help_text="Full name of the candidate"
    )
    
    # Optional personal information
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Phone number"
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Current location (City, State, Country)"
    )
    
    # Professional information
    current_position = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Current job title/position"
    )
    current_company = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Current company name"
    )
    experience_years = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Total years of experience"
    )
    
    # Skills and competencies (from the image)
    professional_skills = models.JSONField(
        default=list,
        blank=True,
        help_text="List of professional skills (e.g., Problem Solving, Design System, etc.)"
    )
    
    # Application information
    applied_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the candidate first applied"
    )
    
    # Hiring status
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
        default='applied',
        help_text="Current status in the hiring process"
    )
    
    # Scoring information (from the image)
    hr_interview_score = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        blank=True,
        null=True,
        help_text="HR Interview score (0.0 - 5.0)"
    )
    portfolio_review_score = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        blank=True,
        null=True,
        help_text="Portfolio Review score (0.0 - 5.0)"
    )
    design_test_score = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        blank=True,
        null=True,
        help_text="Design Test score (0.0 - 5.0)"
    )
    overall_score = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        blank=True,
        null=True,
        help_text="Overall candidate score (0.0 - 5.0)"
    )
    
    # Skill matching percentage (from the image)
    skill_match_percentage = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Percentage of skills matched (0-100)"
    )
    matched_skills_count = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Number of skills matched"
    )
    total_skills_count = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Total number of required skills"
    )
    
    # Additional information
    linkedin_url = models.URLField(
        blank=True,
        null=True,
        help_text="LinkedIn profile URL"
    )
    portfolio_url = models.URLField(
        blank=True,
        null=True,
        help_text="Portfolio website URL"
    )
    salary_expectation = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Expected salary"
    )
    availability_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date when candidate can start"
    )
    
    # Internal notes
    internal_notes = models.TextField(
        blank=True,
        help_text="Internal notes about the candidate (not visible to candidate)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Relations to other models (will be connected through foreign keys in other models)
    # - MPR connection (through CandidateMPR model)
    # - Email connection (through CandidateEmail model)
    # - Interview connection (through Interview model)
    
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
    
    @property
    def latest_status_update(self):
        """Get the most recent status update"""
        return self.status_updates.first()
    
    @property
    def active_interviews(self):
        """Get active interviews for this candidate"""
        return self.interviews.filter(status__in=['scheduled', 'in_progress'])
    
    @property
    def completed_interviews(self):
        """Get completed interviews for this candidate"""
        return self.interviews.filter(status='completed')
    
    def calculate_overall_score(self):
        """Calculate overall score based on individual scores"""
        scores = []
        if self.hr_interview_score:
            scores.append(float(self.hr_interview_score))
        if self.portfolio_review_score:
            scores.append(float(self.portfolio_review_score))
        if self.design_test_score:
            scores.append(float(self.design_test_score))
        
        if scores:
            self.overall_score = sum(scores) / len(scores)
            return self.overall_score
        return None
    
    def update_skill_matching(self, required_skills, candidate_skills):
        """Update skill matching percentage and counts"""
        if not required_skills:
            return
        
        matched_skills = set(required_skills) & set(candidate_skills)
        self.matched_skills_count = len(matched_skills)
        self.total_skills_count = len(required_skills)
        self.skill_match_percentage = int((len(matched_skills) / len(required_skills)) * 100)


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
        blank=True,
        null=True
    )
    new_status = models.CharField(
        max_length=20,
        choices=Candidate.HIRING_STATUS_CHOICES
    )
    reason = models.TextField(
        blank=True,
        help_text="Reason for status change"
    )
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


class CandidateEmail(models.Model):
    """Email communications with candidates"""
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name='emails'
    )
    
    # Email details
    subject = models.CharField(max_length=500)
    body = models.TextField()
    from_email = models.EmailField()
    to_email = models.EmailField()
    cc_emails = models.JSONField(
        default=list,
        blank=True,
        help_text="List of CC email addresses"
    )
    bcc_emails = models.JSONField(
        default=list,
        blank=True,
        help_text="List of BCC email addresses"
    )
    
    # Email metadata
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
    
    is_inbound = models.BooleanField(
        default=True,
        help_text="True if email is from candidate to us, False if from us to candidate"
    )
    is_read = models.BooleanField(default=False)
    
    # External email system integration
    external_email_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="ID from external email system (Gmail, Outlook, etc.)"
    )
    
    # Timestamps
    sent_at = models.DateTimeField()
    received_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'candidate_emails'
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['candidate', '-sent_at']),
            models.Index(fields=['email_type']),
            models.Index(fields=['is_inbound']),
        ]
    
    def __str__(self):
        direction = "From" if self.is_inbound else "To"
        return f"{direction} {self.candidate.name}: {self.subject}"


class EmailAttachment(models.Model):
    """Attachments for candidate emails"""
    email = models.ForeignKey(
        CandidateEmail,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
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
            ('other', 'Other Document'),
        ],
        default='other'
    )
    mime_type = models.CharField(max_length=100)
    
    # File storage
    file = models.FileField(
        upload_to=candidate_attachment_upload_path,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'gif']
            )
        ]
    )
    
    # Visibility control (for MPR connection)
    is_visible_to_line_manager = models.BooleanField(
        default=False,
        help_text="Whether this attachment is visible to line managers and others (besides recruiter)"
    )
    is_primary_cv = models.BooleanField(
        default=False,
        help_text="Whether this is the primary CV selected by recruiter"
    )
    
    # Processing information
    is_processed = models.BooleanField(
        default=False,
        help_text="Whether the attachment has been processed (e.g., text extracted)"
    )
    extracted_text = models.TextField(
        blank=True,
        help_text="Text extracted from the document for searching"
    )
    
    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'candidate_email_attachments'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['candidate', '-uploaded_at']),
            models.Index(fields=['file_type']),
            models.Index(fields=['is_visible_to_line_manager']),
            models.Index(fields=['is_primary_cv']),
        ]
    
    def __str__(self):
        return f"{self.candidate.name}: {self.original_file_name}"
    
    def delete(self, *args, **kwargs):
        """Delete the file when the model instance is deleted"""
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        super().delete(*args, **kwargs)


class CandidateMPR(models.Model):
    """Many-to-many relationship between Candidate and MPR with additional fields"""
    candidate = models.ForeignKey(
        Candidate,
        on_delete=models.CASCADE,
        related_name='mpr_applications'
    )
    # Assuming MPR model exists in the mpr app
    mpr = models.ForeignKey(
        'mpr.MPR',  # Reference to MPR model in mpr app
        on_delete=models.CASCADE,
        related_name='candidate_applications'
    )
    
    # Application specific information
    application_stage = models.CharField(
        max_length=50,
        choices=[
            ('applied', 'Applied'),
            ('recruiter_shortlist', 'Recruiter Short List'),
            ('line_manager_shortlist', 'Line Manager Short List'),
            ('selected', 'Selected Candidate'),
            ('rejected', 'Rejected'),
        ],
        default='applied'
    )
    
    # Primary CV for this specific MPR application
    primary_cv = models.ForeignKey(
        EmailAttachment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='primary_cv_for_mprs',
        help_text="Primary CV attachment for this MPR (visible to line managers)"
    )
    
    # Application notes
    recruiter_notes = models.TextField(
        blank=True,
        help_text="Recruiter's notes about this application"
    )
    line_manager_notes = models.TextField(
        blank=True,
        help_text="Line manager's notes about this application"
    )
    
    # Scoring for this specific MPR
    technical_fit_score = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        blank=True,
        null=True,
        help_text="Technical fit score for this specific role (0.0 - 5.0)"
    )
    cultural_fit_score = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        blank=True,
        null=True,
        help_text="Cultural fit score for this specific role (0.0 - 5.0)"
    )
    
    # Timestamps
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
        indexes = [
            models.Index(fields=['mpr', 'application_stage']),
            models.Index(fields=['candidate', '-applied_at']),
        ]
    
    def __str__(self):
        return f"{self.candidate.name} → {self.mpr.job_title} ({self.application_stage})"
    
    def save(self, *args, **kwargs):
        """Ensure primary CV is set to visible for line managers"""
        super().save(*args, **kwargs)
        if self.primary_cv:
            self.primary_cv.is_visible_to_line_manager = True
            self.primary_cv.save(update_fields=['is_visible_to_line_manager'])