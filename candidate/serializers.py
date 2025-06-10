from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Candidate, CandidateStatusUpdate, CandidateEmail, 
    EmailAttachment, CandidateMPR
)
from django.conf import settings


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user information serializer"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name', 'email']


class EmailAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for email attachments"""
    file_url = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = EmailAttachment
        fields = [
            'id', 'file_name', 'original_file_name', 'file_size', 'file_size_mb',
            'file_type', 'mime_type', 'file_url', 'is_visible_to_line_manager',
            'is_primary_cv', 'is_processed', 'uploaded_at'
        ]
        read_only_fields = ['id', 'file_size', 'uploaded_at', 'is_processed']
    
    def get_file_url(self, obj):
        """Get the file URL"""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None
    
    def get_file_size_mb(self, obj):
        """Convert file size to MB"""
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return 0


class CandidateEmailSerializer(serializers.ModelSerializer):
    """Serializer for candidate emails"""
    attachments = EmailAttachmentSerializer(many=True, read_only=True)
    attachments_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CandidateEmail
        fields = [
            'id', 'subject', 'body', 'from_email', 'to_email', 'cc_emails',
            'bcc_emails', 'email_type', 'is_inbound', 'is_read',
            'external_email_id', 'sent_at', 'received_at', 'attachments',
            'attachments_count'
        ]
        read_only_fields = ['id', 'received_at']
    
    def get_attachments_count(self, obj):
        """Get the number of attachments"""
        return obj.attachments.count()


class CandidateStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for candidate status updates"""
    updated_by = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = CandidateStatusUpdate
        fields = [
            'id', 'previous_status', 'new_status', 'reason',
            'updated_by', 'updated_at'
        ]
        read_only_fields = ['id', 'updated_at']


class CandidateMPRSerializer(serializers.ModelSerializer):
    """Serializer for candidate MPR relationships"""
    mpr_title = serializers.CharField(source='mpr.job_title.title', read_only=True)
    mpr_number = serializers.CharField(source='mpr.mpr_number', read_only=True)
    mpr_status = serializers.CharField(source='mpr.status', read_only=True)
    primary_cv = EmailAttachmentSerializer(read_only=True)
    updated_by = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = CandidateMPR
        fields = [
            'id', 'mpr', 'mpr_title', 'mpr_number', 'mpr_status',
            'application_stage', 'primary_cv', 'recruiter_notes',
            'line_manager_notes', 'technical_fit_score', 'cultural_fit_score',
            'applied_at', 'updated_at', 'updated_by'
        ]
        read_only_fields = ['id', 'applied_at', 'updated_at']


class CandidateListSerializer(serializers.ModelSerializer):
    """Serializer for candidate list view"""
    latest_status_update = serializers.SerializerMethodField()
    active_interviews_count = serializers.SerializerMethodField()
    completed_interviews_count = serializers.SerializerMethodField()
    emails_count = serializers.SerializerMethodField()
    attachments_count = serializers.SerializerMethodField()
    applications_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Candidate
        fields = [
            'id', 'email', 'name', 'phone', 'location', 'current_position',
            'current_company', 'experience_years', 'hiring_status',
            'overall_score', 'skill_match_percentage', 'applied_at',
            'latest_status_update', 'active_interviews_count',
            'completed_interviews_count', 'emails_count', 'attachments_count',
            'applications_count'
        ]
        read_only_fields = ['id', 'applied_at']
    
    def get_latest_status_update(self, obj):
        """Get the latest status update"""
        latest_update = obj.status_updates.first()
        if latest_update:
            return {
                'status': latest_update.new_status,
                'updated_at': latest_update.updated_at,
                'updated_by': latest_update.updated_by.get_full_name() if latest_update.updated_by else None
            }
        return None
    
    def get_active_interviews_count(self, obj):
        """Get count of active interviews"""
        return obj.interviews.filter(status__in=['scheduled', 'confirmed', 'in_progress']).count()
    
    def get_completed_interviews_count(self, obj):
        """Get count of completed interviews"""
        return obj.interviews.filter(status='completed').count()
    
    def get_emails_count(self, obj):
        """Get count of emails"""
        return obj.emails.count()
    
    def get_attachments_count(self, obj):
        """Get count of attachments"""
        return obj.attachments.count()
    
    def get_applications_count(self, obj):
        """Get count of MPR applications"""
        return obj.mpr_applications.count()


class CandidateDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for candidate"""
    status_updates = CandidateStatusUpdateSerializer(many=True, read_only=True)
    emails = CandidateEmailSerializer(many=True, read_only=True)
    attachments = EmailAttachmentSerializer(many=True, read_only=True)
    mpr_applications = CandidateMPRSerializer(many=True, read_only=True)
    
    # Computed fields
    latest_status_update = serializers.SerializerMethodField()
    active_interviews_count = serializers.SerializerMethodField()
    completed_interviews_count = serializers.SerializerMethodField()
    primary_cv = serializers.SerializerMethodField()
    
    class Meta:
        model = Candidate
        fields = [
            'id', 'email', 'name', 'phone', 'location', 'current_position',
            'current_company', 'experience_years', 'professional_skills',
            'hiring_status', 'hr_interview_score', 'portfolio_review_score',
            'design_test_score', 'overall_score', 'skill_match_percentage',
            'matched_skills_count', 'total_skills_count', 'linkedin_url',
            'portfolio_url', 'salary_expectation', 'availability_date',
            'internal_notes', 'applied_at', 'created_at', 'updated_at',
            'status_updates', 'emails', 'attachments', 'mpr_applications',
            'latest_status_update', 'active_interviews_count',
            'completed_interviews_count', 'primary_cv'
        ]
        read_only_fields = ['id', 'applied_at', 'created_at', 'updated_at']
    
    def get_latest_status_update(self, obj):
        """Get the latest status update"""
        latest_update = obj.status_updates.first()
        if latest_update:
            return CandidateStatusUpdateSerializer(latest_update).data
        return None
    
    def get_active_interviews_count(self, obj):
        """Get count of active interviews"""
        return obj.interviews.filter(status__in=['scheduled', 'confirmed', 'in_progress']).count()
    
    def get_completed_interviews_count(self, obj):
        """Get count of completed interviews"""
        return obj.interviews.filter(status='completed').count()
    
    def get_primary_cv(self, obj):
        """Get the primary CV attachment"""
        primary_cv = obj.attachments.filter(is_primary_cv=True).first()
        if primary_cv:
            return EmailAttachmentSerializer(primary_cv, context=self.context).data
        return None


class CandidateCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating candidates"""
    
    class Meta:
        model = Candidate
        fields = [
            'email', 'name', 'phone', 'location', 'current_position',
            'current_company', 'experience_years', 'professional_skills',
            'hiring_status', 'hr_interview_score', 'portfolio_review_score',
            'design_test_score', 'skill_match_percentage', 'matched_skills_count',
            'total_skills_count', 'linkedin_url', 'portfolio_url',
            'salary_expectation', 'availability_date', 'internal_notes'
        ]
    
    def validate_email(self, value):
        """Validate email uniqueness"""
        if self.instance:
            # For updates, exclude current instance
            if Candidate.objects.filter(email=value).exclude(pk=self.instance.pk).exists():
                raise serializers.ValidationError("A candidate with this email already exists.")
        else:
            # For creation
            if Candidate.objects.filter(email=value).exists():
                raise serializers.ValidationError("A candidate with this email already exists.")
        return value
    
    def validate_skill_match_percentage(self, value):
        """Validate skill match percentage is between 0 and 100"""
        if value is not None and (value < 0 or value > 100):
            raise serializers.ValidationError("Skill match percentage must be between 0 and 100.")
        return value
    
    def validate_scores(self, attrs):
        """Validate that scores are between 0.0 and 5.0"""
        score_fields = ['hr_interview_score', 'portfolio_review_score', 'design_test_score']
        for field in score_fields:
            score = attrs.get(field)
            if score is not None and (score < 0.0 or score > 5.0):
                raise serializers.ValidationError(f"{field} must be between 0.0 and 5.0.")
        return attrs
    
    def validate(self, attrs):
        """Custom validation"""
        attrs = self.validate_scores(attrs)
        return attrs
    
    def create(self, validated_data):
        """Create a new candidate"""
        candidate = Candidate.objects.create(**validated_data)
        
        # Calculate overall score if individual scores are provided
        candidate.calculate_overall_score()
        if candidate.overall_score:
            candidate.save(update_fields=['overall_score'])
        
        return candidate
    
    def update(self, instance, validated_data):
        """Update an existing candidate"""
        # Track status changes
        old_status = instance.hiring_status
        new_status = validated_data.get('hiring_status', old_status)
        
        # Update the instance
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Recalculate overall score
        instance.calculate_overall_score()
        instance.save()
        
        # Create status update record if status changed
        if old_status != new_status:
            CandidateStatusUpdate.objects.create(
                candidate=instance,
                previous_status=old_status,
                new_status=new_status,
                reason="Status updated via API",
                updated_by=self.context.get('request').user if self.context.get('request') else None
            )
        
        return instance


class CandidateEmailCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating candidate emails"""
    
    class Meta:
        model = CandidateEmail
        fields = [
            'subject', 'body', 'from_email', 'to_email', 'cc_emails',
            'bcc_emails', 'email_type', 'is_inbound', 'external_email_id',
            'sent_at'
        ]
    
    def create(self, validated_data):
        """Create a new candidate email"""
        candidate = self.context['candidate']
        return CandidateEmail.objects.create(candidate=candidate, **validated_data)


class EmailAttachmentUploadSerializer(serializers.ModelSerializer):
    """Serializer for uploading email attachments"""
    
    class Meta:
        model = EmailAttachment
        fields = [
            'file', 'original_file_name', 'file_type', 'is_visible_to_line_manager',
            'is_primary_cv'
        ]
    
    def create(self, validated_data):
        """Create a new email attachment"""
        candidate = self.context['candidate']
        email = self.context.get('email')
        
        # Extract file information
        file = validated_data['file']
        validated_data['file_name'] = file.name
        validated_data['file_size'] = file.size
        validated_data['mime_type'] = getattr(file, 'content_type', 'application/octet-stream')
        
        if not validated_data.get('original_file_name'):
            validated_data['original_file_name'] = file.name
        
        return EmailAttachment.objects.create(
            candidate=candidate,
            email=email,
            **validated_data
        )


class CandidateMPRCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating candidate MPR relationships"""
    
    class Meta:
        model = CandidateMPR
        fields = [
            'mpr', 'application_stage', 'primary_cv', 'recruiter_notes',
            'line_manager_notes', 'technical_fit_score', 'cultural_fit_score'
        ]
    
    def validate_technical_fit_score(self, value):
        """Validate technical fit score"""
        if value is not None and (value < 0.0 or value > 5.0):
            raise serializers.ValidationError("Technical fit score must be between 0.0 and 5.0.")
        return value
    
    def validate_cultural_fit_score(self, value):
        """Validate cultural fit score"""
        if value is not None and (value < 0.0 or value > 5.0):
            raise serializers.ValidationError("Cultural fit score must be between 0.0 and 5.0.")
        return value
    
    def create(self, validated_data):
        """Create a new candidate MPR relationship"""
        candidate = self.context['candidate']
        return CandidateMPR.objects.create(
            candidate=candidate,
            updated_by=self.context.get('request').user if self.context.get('request') else None,
            **validated_data
        )
    
    def update(self, instance, validated_data):
        """Update an existing candidate MPR relationship"""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.updated_by = self.context.get('request').user if self.context.get('request') else None
        instance.save()
        
        return instance