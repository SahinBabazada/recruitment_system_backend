# candidate/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Candidate, CandidateWorkExperience, CandidateEducation, 
    CandidateProject, CandidateReference, CandidateEmailConnection,
    CandidateAttachment, CandidateStatusUpdate, CandidateMPR
)

User = get_user_model()

# Try to import email service models with fallback
try:
    from email_service.models import EmailMessage
except ImportError:
    EmailMessage = None


class CandidateWorkExperienceSerializer(serializers.ModelSerializer):
    """Serializer for candidate work experience"""
    
    duration_text = serializers.SerializerMethodField()
    is_current_display = serializers.SerializerMethodField()
    
    class Meta:
        model = CandidateWorkExperience
        fields = [
            'id', 'company_name', 'position_title', 'department', 'location',
            'start_date', 'end_date', 'is_current', 'employment_type',
            'job_description', 'key_achievements', 'technologies_used',
            'display_order', 'duration_text', 'is_current_display',
            'created_at', 'updated_at'
        ]
    
    def get_duration_text(self, obj):
        """Calculate and format duration"""
        try:
            from datetime import date
            from dateutil.relativedelta import relativedelta
            
            start = obj.start_date
            end = obj.end_date if obj.end_date else date.today()
            
            delta = relativedelta(end, start)
            
            if delta.years > 0:
                if delta.months > 0:
                    return f"{delta.years} year{'s' if delta.years > 1 else ''}, {delta.months} month{'s' if delta.months > 1 else ''}"
                else:
                    return f"{delta.years} year{'s' if delta.years > 1 else ''}"
            elif delta.months > 0:
                return f"{delta.months} month{'s' if delta.months > 1 else ''}"
            else:
                return "Less than a month"
        except ImportError:
            # Fallback if dateutil not available
            return f"{obj.start_date} - {obj.end_date or 'Present'}"
    
    def get_is_current_display(self, obj):
        return "Current" if obj.is_current else "Past"


class CandidateEducationSerializer(serializers.ModelSerializer):
    """Serializer for candidate education"""
    
    duration_text = serializers.SerializerMethodField()
    degree_display = serializers.SerializerMethodField()
    
    class Meta:
        model = CandidateEducation
        fields = [
            'id', 'institution_name', 'degree_type', 'field_of_study',
            'specialization', 'start_date', 'end_date', 'is_current',
            'grade_gpa', 'location', 'thesis_title', 'honors_awards',
            'relevant_coursework', 'display_order', 'duration_text',
            'degree_display', 'created_at', 'updated_at'
        ]
    
    def get_duration_text(self, obj):
        """Calculate and format duration"""
        from datetime import date
        
        start = obj.start_date
        end = obj.end_date if obj.end_date else date.today()
        
        return f"{start.year} - {end.year if not obj.is_current else 'Present'}"
    
    def get_degree_display(self, obj):
        """Format degree display"""
        degree = obj.get_degree_type_display()
        if obj.field_of_study:
            return f"{degree} in {obj.field_of_study}"
        return degree


class CandidateProjectSerializer(serializers.ModelSerializer):
    """Serializer for candidate projects"""
    
    duration_text = serializers.SerializerMethodField()
    links_available = serializers.SerializerMethodField()
    
    class Meta:
        model = CandidateProject
        fields = [
            'id', 'project_name', 'project_type', 'description',
            'technologies_used', 'start_date', 'end_date',
            'project_url', 'github_url', 'demo_url',
            'display_order', 'is_featured', 'duration_text',
            'links_available', 'created_at', 'updated_at'
        ]
    
    def get_duration_text(self, obj):
        """Format project duration"""
        if obj.start_date:
            start_year = obj.start_date.year
            end_year = obj.end_date.year if obj.end_date else "Present"
            return f"{start_year} - {end_year}"
        return "Date not specified"
    
    def get_links_available(self, obj):
        """List available links"""
        links = []
        if obj.project_url:
            links.append('project')
        if obj.github_url:
            links.append('github')
        if obj.demo_url:
            links.append('demo')
        return links


class CandidateReferenceSerializer(serializers.ModelSerializer):
    """Serializer for candidate references"""
    
    relationship_display = serializers.SerializerMethodField()
    contact_info = serializers.SerializerMethodField()
    
    class Meta:
        model = CandidateReference
        fields = [
            'id', 'reference_name', 'reference_title', 'company_name',
            'relationship', 'relationship_display', 'email', 'phone', 
            'permission_to_contact', 'contact_preference', 'notes',
            'contact_info', 'created_at', 'updated_at'
        ]
    
    def get_relationship_display(self, obj):
        return obj.get_relationship_display()
    
    def get_contact_info(self, obj):
        """Formatted contact information"""
        info = []
        if obj.email:
            info.append(f"Email: {obj.email}")
        if obj.phone:
            info.append(f"Phone: {obj.phone}")
        return " | ".join(info)


class EmailMessageSimpleSerializer(serializers.ModelSerializer):
    """Simple serializer for EmailMessage"""
    
    class Meta:
        model = EmailMessage if EmailMessage else None
        fields = [
            'id', 'subject', 'from_email', 'from_name', 
            'sent_datetime', 'received_datetime', 'is_read',
            'has_attachments', 'importance'
        ] if EmailMessage else []


class CandidateEmailConnectionSerializer(serializers.ModelSerializer):
    """Serializer for candidate email connections"""
    
    email_message = serializers.SerializerMethodField()
    attachments_count = serializers.SerializerMethodField()
    email_type_display = serializers.SerializerMethodField()
    
    class Meta:
        model = CandidateEmailConnection
        fields = [
            'id', 'email_message', 'email_type', 'email_type_display', 
            'is_inbound', 'requires_response', 'is_responded', 
            'internal_notes', 'attachments_count', 'created_at', 'updated_at'
        ]
    
    def get_email_message(self, obj):
        """Get email message data"""
        if obj.email_message and EmailMessage:
            return EmailMessageSimpleSerializer(obj.email_message).data
        return None
    
    def get_attachments_count(self, obj):
        return obj.attachments.count()
    
    def get_email_type_display(self, obj):
        return obj.get_email_type_display()


class CandidateAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for candidate attachments"""
    
    file_url = serializers.SerializerMethodField()
    file_size_display = serializers.SerializerMethodField()
    uploaded_by_name = serializers.SerializerMethodField()
    file_type_display = serializers.SerializerMethodField()
    
    class Meta:
        model = CandidateAttachment
        fields = [
            'id', 'file_name', 'original_file_name', 'file_size',
            'file_size_display', 'file_type', 'file_type_display', 
            'mime_type', 'file_url', 'is_primary_cv', 'is_latest_version', 
            'is_processed', 'description', 'uploaded_by_name', 
            'created_at', 'updated_at'
        ]
    
    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None
    
    def get_file_size_display(self, obj):
        """Format file size in human readable format"""
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def get_uploaded_by_name(self, obj):
        return obj.uploaded_by.get_full_name() if obj.uploaded_by else None
    
    def get_file_type_display(self, obj):
        return obj.get_file_type_display()


class CandidateStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for candidate status updates"""
    
    updated_by_name = serializers.SerializerMethodField()
    previous_status_display = serializers.SerializerMethodField()
    new_status_display = serializers.SerializerMethodField()
    
    class Meta:
        model = CandidateStatusUpdate
        fields = [
            'id', 'previous_status', 'previous_status_display',
            'new_status', 'new_status_display', 'reason',
            'updated_by_name', 'updated_at'
        ]
    
    def get_updated_by_name(self, obj):
        return obj.updated_by.get_full_name() if obj.updated_by else 'System'
    
    def get_previous_status_display(self, obj):
        return dict(Candidate.HIRING_STATUS_CHOICES).get(obj.previous_status, obj.previous_status)
    
    def get_new_status_display(self, obj):
        return dict(Candidate.HIRING_STATUS_CHOICES).get(obj.new_status, obj.new_status)


class CandidateMPRSerializer(serializers.ModelSerializer):
    """Serializer for candidate MPR applications"""
    
    mpr_title = serializers.SerializerMethodField()
    mpr_number = serializers.SerializerMethodField()
    mpr_department = serializers.SerializerMethodField()
    primary_cv_file = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()
    application_stage_display = serializers.SerializerMethodField()
    
    class Meta:
        model = CandidateMPR
        fields = [
            'id', 'mpr', 'mpr_title', 'mpr_number', 'mpr_department',
            'application_stage', 'application_stage_display', 'primary_cv', 
            'primary_cv_file', 'application_notes', 'recruiter_notes', 
            'applied_at', 'updated_at', 'updated_by_name'
        ]
    
    def get_mpr_title(self, obj):
        if obj.mpr and hasattr(obj.mpr, 'job_title') and obj.mpr.job_title:
            return obj.mpr.job_title.title
        return None
    
    def get_mpr_number(self, obj):
        return obj.mpr.mpr_number if obj.mpr else None
    
    def get_mpr_department(self, obj):
        if obj.mpr and hasattr(obj.mpr, 'department') and obj.mpr.department:
            return obj.mpr.department.name
        return None
    
    def get_primary_cv_file(self, obj):
        if obj.primary_cv and obj.primary_cv.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.primary_cv.file.url)
        return None
    
    def get_updated_by_name(self, obj):
        return obj.updated_by.get_full_name() if obj.updated_by else None
    
    def get_application_stage_display(self, obj):
        return obj.get_application_stage_display()


class CandidateListSerializer(serializers.ModelSerializer):
    """List serializer for candidates"""
    
    hiring_status_display = serializers.SerializerMethodField()
    latest_status_update = serializers.SerializerMethodField()
    work_experiences_count = serializers.SerializerMethodField()
    education_count = serializers.SerializerMethodField()
    projects_count = serializers.SerializerMethodField()
    attachments_count = serializers.SerializerMethodField()
    emails_count = serializers.SerializerMethodField()
    applications_count = serializers.SerializerMethodField()
    primary_cv = serializers.SerializerMethodField()
    experience_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = Candidate
        fields = [
            'id', 'email', 'name', 'phone', 'location',
            'current_position', 'current_company', 'experience_years',
            'hiring_status', 'hiring_status_display', 'overall_score',
            'skill_match_percentage', 'salary_expectation', 'salary_currency',
            'availability_date', 'applied_at', 'created_at', 'updated_at',
            'latest_status_update', 'work_experiences_count', 'education_count',
            'projects_count', 'attachments_count', 'emails_count',
            'applications_count', 'primary_cv', 'experience_summary'
        ]
    
    def get_hiring_status_display(self, obj):
        return obj.get_hiring_status_display()
    
    def get_latest_status_update(self, obj):
        latest = obj.status_updates.first()
        if latest:
            return CandidateStatusUpdateSerializer(latest).data
        return None
    
    def get_work_experiences_count(self, obj):
        return obj.work_experiences.count()
    
    def get_education_count(self, obj):
        return obj.education_history.count()
    
    def get_projects_count(self, obj):
        return obj.projects.count()
    
    def get_attachments_count(self, obj):
        return obj.attachments.count()
    
    def get_emails_count(self, obj):
        return obj.email_connections.count()
    
    def get_applications_count(self, obj):
        return obj.mpr_applications.count()
    
    def get_primary_cv(self, obj):
        primary_cv = obj.attachments.filter(is_primary_cv=True).first()
        if primary_cv:
            return CandidateAttachmentSerializer(primary_cv, context=self.context).data
        return None
    
    def get_experience_summary(self, obj):
        """Get a summary of candidate's experience"""
        experiences = obj.work_experiences.all()[:3]  # Latest 3 experiences
        if experiences:
            return [
                {
                    'company': exp.company_name,
                    'position': exp.position_title,
                    'is_current': exp.is_current
                }
                for exp in experiences
            ]
        return []


class CandidateDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for candidate"""
    
    # Related data
    work_experiences = CandidateWorkExperienceSerializer(many=True, read_only=True)
    education_history = CandidateEducationSerializer(many=True, read_only=True)
    projects = CandidateProjectSerializer(many=True, read_only=True)
    references = CandidateReferenceSerializer(many=True, read_only=True)
    email_connections = CandidateEmailConnectionSerializer(many=True, read_only=True)
    attachments = CandidateAttachmentSerializer(many=True, read_only=True)
    status_updates = CandidateStatusUpdateSerializer(many=True, read_only=True)
    mpr_applications = CandidateMPRSerializer(many=True, read_only=True)
    
    # Computed fields
    hiring_status_display = serializers.SerializerMethodField()
    total_experience_years = serializers.SerializerMethodField()
    latest_education = serializers.SerializerMethodField()
    featured_projects = serializers.SerializerMethodField()
    primary_cv = serializers.SerializerMethodField()
    unread_emails_count = serializers.SerializerMethodField()
    skills_summary = serializers.SerializerMethodField()
    contact_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Candidate
        fields = [
            'id', 'email', 'name', 'phone', 'alternative_phone', 'location',
            'address', 'date_of_birth', 'nationality', 'current_position',
            'current_company', 'professional_summary', 'experience_years',
            'professional_skills', 'technical_skills', 'soft_skills',
            'languages', 'certifications', 'linkedin_url', 'portfolio_url',
            'github_url', 'personal_website', 'hiring_status', 'hiring_status_display',
            'overall_score', 'skill_match_percentage', 'matched_skills_count',
            'total_skills_count', 'salary_expectation', 'salary_currency',
            'availability_date', 'notice_period_days', 'internal_notes',
            'applied_at', 'created_at', 'updated_at',
            
            # Related data
            'work_experiences', 'education_history', 'projects', 'references',
            'email_connections', 'attachments', 'status_updates', 'mpr_applications',
            
            # Computed fields
            'total_experience_years', 'latest_education', 'featured_projects',
            'primary_cv', 'unread_emails_count', 'skills_summary', 'contact_info'
        ]
        read_only_fields = ['id', 'applied_at', 'created_at', 'updated_at']
    
    def get_hiring_status_display(self, obj):
        return obj.get_hiring_status_display()
    
    def get_total_experience_years(self, obj):
        """Calculate total experience from work history"""
        try:
            from datetime import date
            from dateutil.relativedelta import relativedelta
            
            total_months = 0
            for exp in obj.work_experiences.all():
                start = exp.start_date
                end = exp.end_date if exp.end_date else date.today()
                delta = relativedelta(end, start)
                total_months += (delta.years * 12) + delta.months
            
            return round(total_months / 12, 1)
        except ImportError:
            # Fallback if dateutil not available
            return obj.experience_years
    
    def get_latest_education(self, obj):
        """Get the most recent education"""
        latest = obj.education_history.first()
        if latest:
            return CandidateEducationSerializer(latest).data
        return None
    
    def get_featured_projects(self, obj):
        """Get featured projects"""
        featured = obj.projects.filter(is_featured=True)
        return CandidateProjectSerializer(featured, many=True).data
    
    def get_primary_cv(self, obj):
        """Get primary CV"""
        primary_cv = obj.attachments.filter(is_primary_cv=True).first()
        if primary_cv:
            return CandidateAttachmentSerializer(primary_cv, context=self.context).data
        return None
    
    def get_unread_emails_count(self, obj):
        """Count unread emails"""
        return obj.email_connections.filter(
            email_message__is_read=False,
            is_inbound=True
        ).count()
    
    def get_skills_summary(self, obj):
        """Get summary of all skills"""
        summary = {}
        
        if obj.professional_skills:
            summary['professional'] = obj.professional_skills
        if obj.technical_skills:
            summary['technical'] = obj.technical_skills
        if obj.soft_skills:
            summary['soft'] = obj.soft_skills
        if obj.languages:
            summary['languages'] = obj.languages
        if obj.certifications:
            summary['certifications'] = obj.certifications
        
        # Count total skills
        total_skills = 0
        for skill_list in summary.values():
            if isinstance(skill_list, list):
                total_skills += len(skill_list)
        
        summary['total_count'] = total_skills
        return summary
    
    def get_contact_info(self, obj):
        """Get formatted contact information"""
        contact = {
            'primary_email': obj.email,
            'primary_phone': obj.phone,
        }
        
        if obj.alternative_phone:
            contact['alternative_phone'] = obj.alternative_phone
        if obj.linkedin_url:
            contact['linkedin'] = obj.linkedin_url
        if obj.portfolio_url:
            contact['portfolio'] = obj.portfolio_url
        if obj.github_url:
            contact['github'] = obj.github_url
        if obj.personal_website:
            contact['website'] = obj.personal_website
        
        return contact


class CandidateCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating candidates"""
    
    class Meta:
        model = Candidate
        fields = [
            'id','email', 'name', 'phone', 'alternative_phone', 'location',
            'address', 'date_of_birth', 'nationality', 'current_position',
            'current_company', 'professional_summary', 'experience_years',
            'professional_skills', 'technical_skills', 'soft_skills',
            'languages', 'certifications', 'linkedin_url', 'portfolio_url',
            'github_url', 'personal_website', 'hiring_status',
            'salary_expectation', 'salary_currency', 'availability_date',
            'notice_period_days', 'internal_notes'
        ]
    
    def validate_email(self, value):
        """Validate email uniqueness"""
        if self.instance:
            # For updates, exclude current instance
            if Candidate.objects.exclude(pk=self.instance.pk).filter(email=value).exists():
                raise serializers.ValidationError("A candidate with this email already exists.")
        else:
            # For creates
            if Candidate.objects.filter(email=value).exists():
                raise serializers.ValidationError("A candidate with this email already exists.")
        return value
    
    def validate_experience_years(self, value):
        """Validate experience years"""
        if value is not None and value > 50:
            raise serializers.ValidationError("Experience years cannot exceed 50.")
        return value
    
    def validate_salary_expectation(self, value):
        """Validate salary expectation"""
        if value is not None and value <= 0:
            raise serializers.ValidationError("Salary expectation must be positive.")
        return value
    
    def validate_professional_skills(self, value):
        """Validate professional skills format"""
        if value and not isinstance(value, list):
            raise serializers.ValidationError("Professional skills must be a list.")
        return value
    
    def validate_technical_skills(self, value):
        """Validate technical skills format"""
        if value and not isinstance(value, list):
            raise serializers.ValidationError("Technical skills must be a list.")
        return value
    
    def validate_languages(self, value):
        """Validate languages format"""
        if value and not isinstance(value, list):
            raise serializers.ValidationError("Languages must be a list.")
        return value


class CandidateStatsSerializer(serializers.Serializer):
    """Serializer for candidate statistics"""
    
    total_candidates = serializers.IntegerField()
    by_status = serializers.DictField()
    by_experience_range = serializers.DictField()
    by_location = serializers.DictField()
    recent_applications = serializers.IntegerField()
    average_score = serializers.FloatField()
    
    class Meta:
        fields = [
            'total_candidates', 'by_status', 'by_experience_range',
            'by_location', 'recent_applications', 'average_score'
        ]


class CandidateBulkUpdateSerializer(serializers.Serializer):
    """Serializer for bulk candidate operations"""
    
    candidate_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=100
    )
    action = serializers.ChoiceField(choices=[
        ('update_status', 'Update Status'),
        ('assign_recruiter', 'Assign Recruiter'),
        ('add_note', 'Add Note'),
        ('export', 'Export Data')
    ])
    
    # Optional fields based on action
    status = serializers.ChoiceField(
        choices=Candidate.HIRING_STATUS_CHOICES,
        required=False
    )
    recruiter_id = serializers.IntegerField(required=False)
    note = serializers.CharField(max_length=1000, required=False)
    reason = serializers.CharField(max_length=500, required=False)
    
    def validate(self, data):
        action = data.get('action')
        
        if action == 'update_status' and not data.get('status'):
            raise serializers.ValidationError("Status is required for update_status action.")
        
        if action == 'assign_recruiter' and not data.get('recruiter_id'):
            raise serializers.ValidationError("Recruiter ID is required for assign_recruiter action.")
        
        if action == 'add_note' and not data.get('note'):
            raise serializers.ValidationError("Note is required for add_note action.")
        
        return data


# Nested serializers for creating candidates with related data
class CandidateWithExperienceSerializer(CandidateCreateUpdateSerializer):
    """Serializer for creating candidate with work experience"""
    
    work_experiences = CandidateWorkExperienceSerializer(many=True, required=False)
    education_history = CandidateEducationSerializer(many=True, required=False)
    projects = CandidateProjectSerializer(many=True, required=False)
    references = CandidateReferenceSerializer(many=True, required=False)
    
    class Meta(CandidateCreateUpdateSerializer.Meta):
        fields = CandidateCreateUpdateSerializer.Meta.fields + [
            'work_experiences', 'education_history', 'projects', 'references'
        ]
    
    def create(self, validated_data):
        work_experiences_data = validated_data.pop('work_experiences', [])
        education_data = validated_data.pop('education_history', [])
        projects_data = validated_data.pop('projects', [])
        references_data = validated_data.pop('references', [])
        
        candidate = Candidate.objects.create(**validated_data)
        
        # Create related objects
        for exp_data in work_experiences_data:
            CandidateWorkExperience.objects.create(candidate=candidate, **exp_data)
        
        for edu_data in education_data:
            CandidateEducation.objects.create(candidate=candidate, **edu_data)
        
        for proj_data in projects_data:
            CandidateProject.objects.create(candidate=candidate, **proj_data)
        
        for ref_data in references_data:
            CandidateReference.objects.create(candidate=candidate, **ref_data)
        
        return candidate
    
    def update(self, instance, validated_data):
        # Handle nested updates
        work_experiences_data = validated_data.pop('work_experiences', None)
        education_data = validated_data.pop('education_history', None)
        projects_data = validated_data.pop('projects', None)
        references_data = validated_data.pop('references', None)
        
        # Update candidate fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update related objects if provided
        if work_experiences_data is not None:
            instance.work_experiences.all().delete()
            for exp_data in work_experiences_data:
                CandidateWorkExperience.objects.create(candidate=instance, **exp_data)
        
        if education_data is not None:
            instance.education_history.all().delete()
            for edu_data in education_data:
                CandidateEducation.objects.create(candidate=instance, **edu_data)
        
        if projects_data is not None:
            instance.projects.all().delete()
            for proj_data in projects_data:
                CandidateProject.objects.create(candidate=instance, **proj_data)
        
        if references_data is not None:
            instance.references.all().delete()
            for ref_data in references_data:
                CandidateReference.objects.create(candidate=instance, **ref_data)
        
        return instance