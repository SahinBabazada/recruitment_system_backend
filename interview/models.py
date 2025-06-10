from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from django.contrib.auth import get_user_model

User = get_user_model()

class InterviewRound(models.Model):
    """Define different types of interview rounds"""
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Name of the interview round (e.g., HR Interview, Technical Interview)"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of what this interview round covers"
    )
    typical_duration = models.PositiveIntegerField(
        default=60,
        help_text="Typical duration in minutes"
    )
    sequence_order = models.PositiveIntegerField(
        default=1,
        help_text="Order in the interview process (1 = first round)"
    )
    is_active = models.BooleanField(default=True)
    
    # Scoring criteria for this round
    max_score = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=5.0,
        help_text="Maximum possible score for this round"
    )
    
    # Required evaluation criteria
    evaluation_criteria = models.JSONField(
        default=list,
        blank=True,
        help_text="List of criteria to evaluate (e.g., ['Technical Skills', 'Communication', 'Problem Solving'])"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'interview_rounds'
        ordering = ['sequence_order', 'name']
    
    def __str__(self):
        return f"{self.name} (Order: {self.sequence_order})"


class Interview(models.Model):
    """Interview instances for candidates"""
    
    # Relations
    candidate = models.ForeignKey(
        'candidate.Candidate',  # Reference to Candidate model in candidate app
        on_delete=models.CASCADE,
        related_name='interviews'
    )
    mpr = models.ForeignKey(
        'mpr.MPR',  # Reference to MPR model in mpr app
        on_delete=models.CASCADE,
        related_name='interviews'
    )
    interview_round = models.ForeignKey(
        InterviewRound,
        on_delete=models.PROTECT,
        related_name='interviews'
    )
    
    # Interview details
    title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Custom title for this interview (auto-generated if empty)"
    )
    
    # Scheduling
    scheduled_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Scheduled date and time for the interview"
    )
    duration_minutes = models.PositiveIntegerField(
        default=60,
        help_text="Planned duration in minutes"
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        help_text="Interview location (office, online, phone, etc.)"
    )
    meeting_link = models.URLField(
        blank=True,
        null=True,
        help_text="Video call link for online interviews"
    )
    meeting_details = models.TextField(
        blank=True,
        help_text="Additional meeting instructions or details"
    )
    
    # Status tracking
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rescheduled', 'Rescheduled'),
        ('no_show', 'No Show'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled'
    )
    
    # Actual timing
    actual_start_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the interview actually started"
    )
    actual_end_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the interview actually ended"
    )
    
    # Interview evaluation
    overall_score = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Overall score for this interview (0.0 - 5.0)"
    )
    
    # Detailed feedback
    strengths = models.TextField(
        blank=True,
        help_text="Candidate's strengths observed during the interview"
    )
    weaknesses = models.TextField(
        blank=True,
        help_text="Areas for improvement observed during the interview"
    )
    general_feedback = models.TextField(
        blank=True,
        help_text="General feedback and notes from the interview"
    )
    
    # Decision
    RECOMMENDATION_CHOICES = [
        ('strong_hire', 'Strong Hire'),
        ('hire', 'Hire'),
        ('maybe', 'Maybe/Borderline'),
        ('no_hire', 'No Hire'),
        ('strong_no_hire', 'Strong No Hire'),
    ]
    
    recommendation = models.CharField(
        max_length=20,
        choices=RECOMMENDATION_CHOICES,
        blank=True,
        null=True,
        help_text="Interviewer's hiring recommendation"
    )
    
    # Internal notes
    interviewer_notes = models.TextField(
        blank=True,
        help_text="Private notes from the interviewer"
    )
    preparation_notes = models.TextField(
        blank=True,
        help_text="Notes for interview preparation"
    )
    
    # Timestamps and tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_interviews'
    )
    
    class Meta:
        db_table = 'interviews'
        ordering = ['-scheduled_date']
        indexes = [
            models.Index(fields=['candidate', '-scheduled_date']),
            models.Index(fields=['mpr', '-scheduled_date']),
            models.Index(fields=['status', 'scheduled_date']),
            models.Index(fields=['interview_round', '-scheduled_date']),
        ]
    
    def __str__(self):
        if self.title:
            return self.title
        return f"{self.interview_round.name}: {self.candidate.name} for {self.mpr.job_title}"
    
    def save(self, *args, **kwargs):
        # Auto-generate title if not provided
        if not self.title:
            self.title = f"{self.interview_round.name}: {self.candidate.name}"
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('interview_detail', kwargs={'pk': self.pk})
    
    @property
    def is_upcoming(self):
        """Check if the interview is upcoming"""
        if not self.scheduled_date:
            return False
        return self.scheduled_date > timezone.now() and self.status in ['scheduled', 'confirmed']
    
    @property
    def is_overdue(self):
        """Check if the interview is overdue"""
        if not self.scheduled_date:
            return False
        return self.scheduled_date < timezone.now() and self.status in ['scheduled', 'confirmed']
    
    @property
    def actual_duration_minutes(self):
        """Calculate actual duration of the interview"""
        if self.actual_start_time and self.actual_end_time:
            delta = self.actual_end_time - self.actual_start_time
            return int(delta.total_seconds() / 60)
        return None
    
    def can_be_rescheduled(self):
        """Check if the interview can be rescheduled"""
        return self.status in ['scheduled', 'confirmed', 'rescheduled']
    
    def can_be_cancelled(self):
        """Check if the interview can be cancelled"""
        return self.status in ['scheduled', 'confirmed', 'rescheduled']


class InterviewParticipant(models.Model):
    """Track who participates in interviews (interviewers and observers)"""
    interview = models.ForeignKey(
        Interview,
        on_delete=models.CASCADE,
        related_name='participants'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='interview_participations'
    )
    
    ROLE_CHOICES = [
        ('primary_interviewer', 'Primary Interviewer'),
        ('secondary_interviewer', 'Secondary Interviewer'),
        ('observer', 'Observer'),
        ('technical_interviewer', 'Technical Interviewer'),
        ('hr_interviewer', 'HR Interviewer'),
        ('hiring_manager', 'Hiring Manager'),
    ]
    
    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default='primary_interviewer'
    )
    
    # Individual evaluation from this participant
    individual_score = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="This participant's individual score (0.0 - 5.0)"
    )
    individual_feedback = models.TextField(
        blank=True,
        help_text="This participant's individual feedback"
    )
    individual_recommendation = models.CharField(
        max_length=20,
        choices=Interview.RECOMMENDATION_CHOICES,
        blank=True,
        null=True,
        help_text="This participant's individual recommendation"
    )
    
    # Participation tracking
    attended = models.BooleanField(
        default=True,
        help_text="Whether this participant actually attended the interview"
    )
    joined_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this participant joined the interview"
    )
    left_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this participant left the interview"
    )
    
    # Notification preferences
    send_calendar_invite = models.BooleanField(
        default=True,
        help_text="Whether to send calendar invite to this participant"
    )
    send_reminders = models.BooleanField(
        default=True,
        help_text="Whether to send reminders to this participant"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'interview_participants'
        unique_together = ['interview', 'user']
        ordering = ['role', 'user__first_name']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_role_display()} for {self.interview}"


class InterviewCriteriaEvaluation(models.Model):
    """Detailed evaluation for specific criteria in an interview"""
    interview = models.ForeignKey(
        Interview,
        on_delete=models.CASCADE,
        related_name='criteria_evaluations'
    )
    participant = models.ForeignKey(
        InterviewParticipant,
        on_delete=models.CASCADE,
        related_name='criteria_evaluations',
        null=True,
        blank=True,
        help_text="If null, this is the consolidated evaluation"
    )
    
    # Evaluation details
    criteria_name = models.CharField(
        max_length=100,
        help_text="Name of the criteria being evaluated"
    )
    score = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Score for this specific criteria (0.0 - 5.0)"
    )
    comments = models.TextField(
        blank=True,
        help_text="Comments specific to this criteria"
    )
    weight = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=1.00,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Weight of this criteria in overall score (0.0 - 1.0)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'interview_criteria_evaluations'
        unique_together = ['interview', 'participant', 'criteria_name']
        ordering = ['criteria_name']
    
    def __str__(self):
        participant_name = self.participant.user.get_full_name() if self.participant else "Consolidated"
        return f"{self.interview} - {self.criteria_name} ({participant_name}): {self.score}"


class InterviewQuestion(models.Model):
    """Questions asked during interviews"""
    interview_round = models.ForeignKey(
        InterviewRound,
        on_delete=models.CASCADE,
        related_name='standard_questions'
    )
    
    question_text = models.TextField(help_text="The interview question")
    question_type = models.CharField(
        max_length=30,
        choices=[
            ('behavioral', 'Behavioral'),
            ('technical', 'Technical'),
            ('situational', 'Situational'),
            ('competency', 'Competency-based'),
            ('case_study', 'Case Study'),
            ('general', 'General'),
        ],
        default='general'
    )
    
    # Suggested evaluation criteria for this question
    evaluation_criteria = models.JSONField(
        default=list,
        blank=True,
        help_text="Criteria to evaluate when asking this question"
    )
    
    # Difficulty and timing
    difficulty_level = models.CharField(
        max_length=20,
        choices=[
            ('easy', 'Easy'),
            ('medium', 'Medium'),
            ('hard', 'Hard'),
        ],
        default='medium'
    )
    estimated_time_minutes = models.PositiveIntegerField(
        default=5,
        help_text="Estimated time to answer this question"
    )
    
    # Usage tracking
    is_active = models.BooleanField(default=True)
    usage_count = models.PositiveIntegerField(
        default=0,
        help_text="How many times this question has been used"
    )
    
    # Additional information
    follow_up_questions = models.TextField(
        blank=True,
        help_text="Suggested follow-up questions"
    )
    ideal_answer_points = models.TextField(
        blank=True,
        help_text="Key points to look for in ideal answers"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_interview_questions'
    )
    
    class Meta:
        db_table = 'interview_questions'
        ordering = ['interview_round', 'question_type', 'difficulty_level']
    
    def __str__(self):
        return f"{self.interview_round.name}: {self.question_text[:100]}..."


class InterviewQuestionResponse(models.Model):
    """Candidate responses to specific interview questions"""
    interview = models.ForeignKey(
        Interview,
        on_delete=models.CASCADE,
        related_name='question_responses'
    )
    question = models.ForeignKey(
        InterviewQuestion,
        on_delete=models.CASCADE,
        related_name='responses'
    )
    
    # Custom question if not using a standard one
    custom_question_text = models.TextField(
        blank=True,
        help_text="If asking a custom question not in the question bank"
    )
    
    # Response details
    candidate_answer = models.TextField(
        blank=True,
        help_text="Candidate's response to the question"
    )
    interviewer_notes = models.TextField(
        blank=True,
        help_text="Interviewer's notes about the response"
    )
    
    # Evaluation
    response_score = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Score for this specific response (0.0 - 5.0)"
    )
    
    # Timing
    time_taken_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Time taken to answer this question"
    )
    
    # Asked by which participant
    asked_by = models.ForeignKey(
        InterviewParticipant,
        on_delete=models.CASCADE,
        related_name='asked_questions'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'interview_question_responses'
        unique_together = ['interview', 'question', 'asked_by']
        ordering = ['created_at']
    
    def __str__(self):
        question_text = self.custom_question_text or self.question.question_text
        return f"{self.interview}: {question_text[:50]}..."


class InterviewReschedule(models.Model):
    """Track interview rescheduling history"""
    interview = models.ForeignKey(
        Interview,
        on_delete=models.CASCADE,
        related_name='reschedule_history'
    )
    
    # Previous scheduling details
    previous_date = models.DateTimeField()
    previous_location = models.CharField(max_length=255, blank=True)
    
    # New scheduling details
    new_date = models.DateTimeField()
    new_location = models.CharField(max_length=255, blank=True)
    
    # Reschedule details
    RESCHEDULE_REASON_CHOICES = [
        ('candidate_request', 'Candidate Request'),
        ('interviewer_unavailable', 'Interviewer Unavailable'),
        ('technical_issues', 'Technical Issues'),
        ('emergency', 'Emergency'),
        ('scheduling_conflict', 'Scheduling Conflict'),
        ('other', 'Other'),
    ]
    
    reason = models.CharField(
        max_length=30,
        choices=RESCHEDULE_REASON_CHOICES,
        default='other'
    )
    reason_details = models.TextField(
        blank=True,
        help_text="Additional details about the reschedule reason"
    )
    
    # Who initiated the reschedule
    INITIATED_BY_CHOICES = [
        ('candidate', 'Candidate'),
        ('recruiter', 'Recruiter'),
        ('interviewer', 'Interviewer'),
        ('hr', 'HR'),
        ('system', 'System'),
    ]
    
    initiated_by_type = models.CharField(
        max_length=20,
        choices=INITIATED_BY_CHOICES,
        default='recruiter'
    )
    initiated_by_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='initiated_reschedules'
    )
    
    # Notification tracking
    candidate_notified = models.BooleanField(default=False)
    interviewers_notified = models.BooleanField(default=False)
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'interview_reschedules'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Reschedule: {self.interview} from {self.previous_date} to {self.new_date}"


class InterviewFeedbackTemplate(models.Model):
    """Templates for interview feedback forms"""
    interview_round = models.ForeignKey(
        InterviewRound,
        on_delete=models.CASCADE,
        related_name='feedback_templates'
    )
    
    name = models.CharField(
        max_length=100,
        help_text="Name of the feedback template"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of when to use this template"
    )
    
    # Template structure
    sections = models.JSONField(
        default=list,
        help_text="List of feedback sections with their fields"
    )
    
    # Example structure for sections:
    # [
    #     {
    #         "name": "Technical Skills",
    #         "weight": 0.4,
    #         "fields": [
    #             {"name": "Programming Skills", "type": "score", "required": True},
    #             {"name": "System Design", "type": "score", "required": True},
    #             {"name": "Code Quality", "type": "text", "required": False}
    #         ]
    #     },
    #     {
    #         "name": "Communication",
    #         "weight": 0.3,
    #         "fields": [
    #             {"name": "Clarity", "type": "score", "required": True},
    #             {"name": "Listening Skills", "type": "score", "required": True}
    #         ]
    #     }
    # ]
    
    is_default = models.BooleanField(
        default=False,
        help_text="Whether this is the default template for this interview round"
    )
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_feedback_templates'
    )
    
    class Meta:
        db_table = 'interview_feedback_templates'
        unique_together = ['interview_round', 'name']
        ordering = ['interview_round', 'name']
    
    def __str__(self):
        return f"{self.interview_round.name}: {self.name}"


# Additional utility models for interview management

class InterviewCalendarIntegration(models.Model):
    """Integration with calendar systems"""
    interview = models.OneToOneField(
        Interview,
        on_delete=models.CASCADE,
        related_name='calendar_integration'
    )
    
    # External calendar event IDs
    google_event_id = models.CharField(max_length=255, blank=True, null=True)
    outlook_event_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Sync status
    is_synced = models.BooleanField(default=False)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    sync_errors = models.TextField(
        blank=True,
        help_text="Any errors encountered during calendar sync"
    )
    
    # Event details
    calendar_invite_sent = models.BooleanField(default=False)
    reminder_set = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'interview_calendar_integrations'
    
    def __str__(self):
        return f"Calendar sync for {self.interview}"