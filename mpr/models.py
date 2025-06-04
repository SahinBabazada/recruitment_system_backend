# mpr/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

User = get_user_model()

class Job(models.Model):
    """Job titles available in the organization"""
    title = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_jobs')

    class Meta:
        db_table = 'mpr_jobs'
        ordering = ['title']

    def __str__(self):
        return self.title


class OrganizationalUnit(models.Model):
    """Hierarchical organizational structure (Department > Division > Unit)"""
    TYPE_CHOICES = [
        ('department', 'Department'),
        ('division', 'Division'),
        ('unit', 'Unit'),
    ]
    
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    code = models.CharField(max_length=20, unique=True, help_text="Unique organizational code")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mpr_organizational_units'
        ordering = ['type', 'name']
        unique_together = ['name', 'type', 'parent']

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name} ({self.get_type_display()})"
        return f"{self.name} ({self.get_type_display()})"

    def clean(self):
        # Validate hierarchical structure
        if self.parent:
            if self.type == 'department':
                raise ValidationError("Departments cannot have parents")
            elif self.type == 'division' and self.parent.type != 'department':
                raise ValidationError("Divisions can only belong to departments")
            elif self.type == 'unit' and self.parent.type not in ['department', 'division']:
                raise ValidationError("Units can only belong to departments or divisions")

    def get_full_path(self):
        """Get full organizational path"""
        if self.parent:
            return f"{self.parent.get_full_path()} > {self.name}"
        return self.name


class Location(models.Model):
    """Work locations"""
    name = models.CharField(max_length=200, unique=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    location_type = models.CharField(max_length=50, choices=[
        ('office', 'Office'),
        ('remote', 'Remote'),
        ('hybrid', 'Hybrid'),
        ('client_site', 'Client Site'),
        ('field', 'Field'),
    ], default='office')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mpr_locations'
        ordering = ['name']

    def __str__(self):
        return self.name


class EmploymentType(models.Model):
    """Types of employment"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mpr_employment_types'
        ordering = ['name']

    def __str__(self):
        return self.name


class HiringReason(models.Model):
    """Reasons for hiring"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mpr_hiring_reasons'
        ordering = ['name']

    def __str__(self):
        return self.name


class Employee(models.Model):
    """Employee records (simplified for now)"""
    employee_id = models.CharField(max_length=50, unique=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='employee_profile')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    department = models.ForeignKey(OrganizationalUnit, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'type': 'department'})
    position = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mpr_employees'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.employee_id})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class TechnicalSkill(models.Model):
    """Technical skills that can be required for positions"""
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=50, blank=True, help_text="e.g., Programming, Database, Cloud, etc.")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'mpr_technical_skills'
        ordering = ['category', 'name']

    def __str__(self):
        return self.name


class Language(models.Model):
    """Languages that can be required for positions"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=5, unique=True, help_text="ISO language code (e.g., en, az, tr)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mpr_languages'
        ordering = ['name']

    def __str__(self):
        return self.name


class Competency(models.Model):
    """Core competencies that can be required for positions"""
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=50, blank=True, help_text="e.g., Leadership, Technical, Behavioral")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'mpr_competencies'
        ordering = ['category', 'name']
        verbose_name_plural = 'Competencies'

    def __str__(self):
        return self.name


class ContractDuration(models.Model):
    """Contract duration options"""
    name = models.CharField(max_length=100, unique=True)
    months = models.IntegerField(null=True, blank=True, help_text="Duration in months (null for permanent)")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mpr_contract_durations'
        ordering = ['months']

    def __str__(self):
        return self.name


class MPR(models.Model):
    """Manpower Requisition Form"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('on_hold', 'On Hold'),
        ('closed', 'Closed'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    # Basic Information
    mpr_number = models.CharField(max_length=50, unique=True, blank=True)  # Auto-generated
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')

    # Position Information
    job_title = models.ForeignKey(Job, on_delete=models.PROTECT, related_name='mprs')
    department = models.ForeignKey(OrganizationalUnit, on_delete=models.PROTECT, related_name='mprs', limit_choices_to={'type': 'department'})
    division = models.ForeignKey(OrganizationalUnit, on_delete=models.SET_NULL, null=True, blank=True, related_name='division_mprs', limit_choices_to={'type': 'division'})
    unit = models.ForeignKey(OrganizationalUnit, on_delete=models.SET_NULL, null=True, blank=True, related_name='unit_mprs', limit_choices_to={'type': 'unit'})
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='mprs')
    desired_start_date = models.DateField()
    employment_type = models.ForeignKey(EmploymentType, on_delete=models.PROTECT, related_name='mprs')
    hiring_reason = models.ForeignKey(HiringReason, on_delete=models.PROTECT, related_name='mprs')
    replaced_employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='replacement_mprs')
    business_justification = models.TextField(blank=True)

    # Requirements
    education_requirements = models.TextField(help_text="Education and experience requirements")
    technical_skills = models.ManyToManyField(TechnicalSkill, blank=True, related_name='mprs')
    required_languages = models.ManyToManyField(Language, blank=True, related_name='mprs')
    core_competencies = models.ManyToManyField(Competency, blank=True, related_name='mprs')
    assessment_requirements = models.TextField(blank=True, help_text="Technical tests, case studies, portfolio reviews, etc.")
    contract_duration = models.ForeignKey(ContractDuration, on_delete=models.PROTECT, related_name='mprs')

    # Approval Information
    recruiter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_mprs')
    budget_holder = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='budget_mprs')
    proposed_candidate = models.CharField(max_length=200, blank=True, help_text="If there's a proposed candidate")

    # Audit Information
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_mprs')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_mprs')
    
    # Approval tracking
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_mprs')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='rejected_mprs')
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        db_table = 'mpr_forms'
        ordering = ['-created_at']
        permissions = [
            ('approve_mpr', 'Can approve MPR'),
            ('reject_mpr', 'Can reject MPR'),
            ('view_all_mprs', 'Can view all MPRs'),
        ]

    def __str__(self):
        return f"MPR-{self.mpr_number}: {self.job_title.title} - {self.department.name}"

    def save(self, *args, **kwargs):
        if not self.mpr_number:
            # Generate MPR number
            year = timezone.now().year
            count = MPR.objects.filter(created_at__year=year).count() + 1
            self.mpr_number = f"{year}-{count:04d}"
        super().save(*args, **kwargs)

    def clean(self):
        # Validate organizational hierarchy
        if self.division and self.division.parent != self.department:
            raise ValidationError("Division must belong to the selected department")
        if self.unit and self.unit.parent not in [self.department, self.division]:
            raise ValidationError("Unit must belong to the selected department or division")

    @property
    def applicant_count(self):
        """Count of applicants for this MPR (to be implemented when candidate model is created)"""
        # This will be implemented when we have candidate applications
        return 0

    def can_edit(self, user):
        """Check if user can edit this MPR"""
        if user == self.created_by and self.status == 'draft':
            return True
        if hasattr(user, 'has_permission') and user.has_permission('mpr:edit'):
            return True
        return False

    def can_approve(self, user):
        """Check if user can approve this MPR"""
        if self.status != 'pending':
            return False
        if hasattr(user, 'has_permission') and user.has_permission('mpr:approve'):
            return True
        return False

    def approve(self, user, save=True):
        """Approve the MPR"""
        if not self.can_approve(user):
            raise ValidationError("User cannot approve this MPR")
        
        self.status = 'approved'
        self.approved_by = user
        self.approved_at = timezone.now()
        
        if save:
            self.save(update_fields=['status', 'approved_by', 'approved_at'])

    def reject(self, user, reason='', save=True):
        """Reject the MPR"""
        if not self.can_approve(user):
            raise ValidationError("User cannot reject this MPR")
        
        self.status = 'rejected'
        self.rejected_by = user
        self.rejected_at = timezone.now()
        self.rejection_reason = reason
        
        if save:
            self.save(update_fields=['status', 'rejected_by', 'rejected_at', 'rejection_reason'])


class MPRComment(models.Model):
    """Comments on MPR forms"""
    mpr = models.ForeignKey(MPR, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    is_internal = models.BooleanField(default=False, help_text="Internal comments not visible to requester")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mpr_comments'
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment on {self.mpr.mpr_number} by {self.user.username}"


class MPRStatusHistory(models.Model):
    """Track status changes of MPR forms"""
    mpr = models.ForeignKey(MPR, on_delete=models.CASCADE, related_name='status_history')
    from_status = models.CharField(max_length=20, choices=MPR.STATUS_CHOICES)
    to_status = models.CharField(max_length=20, choices=MPR.STATUS_CHOICES)
    changed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    changed_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True)

    class Meta:
        db_table = 'mpr_status_history'
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.mpr.mpr_number}: {self.from_status} → {self.to_status}"