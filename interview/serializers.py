from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from .models import (
    InterviewRound, Interview, InterviewParticipant, 
    InterviewCriteriaEvaluation, InterviewQuestion,
    InterviewQuestionResponse, InterviewReschedule,
    InterviewFeedbackTemplate, InterviewCalendarIntegration
)


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user information serializer"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name', 'email']


class InterviewRoundSerializer(serializers.ModelSerializer):
    """Serializer for interview rounds"""
    interviews_count = serializers.SerializerMethodField()
    
    class Meta:
        model = InterviewRound
        fields = [
            'id', 'name', 'description', 'typical_duration', 'sequence_order',
            'is_active', 'max_score', 'evaluation_criteria', 'created_at',
            'updated_at', 'interviews_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_interviews_count(self, obj):
        """Get the number of interviews for this round"""
        return obj.interviews.count()


class InterviewParticipantSerializer(serializers.ModelSerializer):
    """Serializer for interview participants"""
    user = UserBasicSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = InterviewParticipant
        fields = [
            'id', 'user', 'user_id', 'role', 'individual_score',
            'individual_feedback', 'individual_recommendation', 'attended',
            'joined_at', 'left_at', 'send_calendar_invite', 'send_reminders',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate_individual_score(self, value):
        """Validate individual score range"""
        if value is not None and (value < 0.0 or value > 5.0):
            raise serializers.ValidationError("Individual score must be between 0.0 and 5.0.")
        return value


class InterviewCriteriaEvaluationSerializer(serializers.ModelSerializer):
    """Serializer for criteria evaluations"""
    participant = InterviewParticipantSerializer(read_only=True)
    participant_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = InterviewCriteriaEvaluation
        fields = [
            'id', 'participant', 'participant_id', 'criteria_name', 'score',
            'comments', 'weight', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate_score(self, value):
        """Validate score range"""
        if value < 0.0 or value > 5.0:
            raise serializers.ValidationError("Score must be between 0.0 and 5.0.")
        return value
    
    def validate_weight(self, value):
        """Validate weight range"""
        if value < 0.0 or value > 1.0:
            raise serializers.ValidationError("Weight must be between 0.0 and 1.0.")
        return value


class InterviewQuestionSerializer(serializers.ModelSerializer):
    """Serializer for interview questions"""
    interview_round = InterviewRoundSerializer(read_only=True)
    interview_round_id = serializers.IntegerField(write_only=True)
    created_by = UserBasicSerializer(read_only=True)
    usage_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = InterviewQuestion
        fields = [
            'id', 'interview_round', 'interview_round_id', 'question_text',
            'question_type', 'evaluation_criteria', 'difficulty_level',
            'estimated_time_minutes', 'is_active', 'usage_count',
            'follow_up_questions', 'ideal_answer_points', 'created_at',
            'updated_at', 'created_by'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'usage_count']


class InterviewQuestionResponseSerializer(serializers.ModelSerializer):
    """Serializer for interview question responses"""
    question = InterviewQuestionSerializer(read_only=True)
    question_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    asked_by = InterviewParticipantSerializer(read_only=True)
    asked_by_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = InterviewQuestionResponse
        fields = [
            'id', 'question', 'question_id', 'custom_question_text',
            'candidate_answer', 'interviewer_notes', 'response_score',
            'time_taken_minutes', 'asked_by', 'asked_by_id', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate_response_score(self, value):
        """Validate response score range"""
        if value is not None and (value < 0.0 or value > 5.0):
            raise serializers.ValidationError("Response score must be between 0.0 and 5.0.")
        return value
    
    def validate(self, attrs):
        """Ensure either question or custom_question_text is provided"""
        question = attrs.get('question_id')
        custom_question = attrs.get('custom_question_text')
        
        if not question and not custom_question:
            raise serializers.ValidationError(
                "Either question or custom_question_text must be provided."
            )
        
        return attrs


class InterviewRescheduleSerializer(serializers.ModelSerializer):
    """Serializer for interview reschedules"""
    initiated_by_user = UserBasicSerializer(read_only=True)
    initiated_by_user_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = InterviewReschedule
        fields = [
            'id', 'previous_date', 'previous_location', 'new_date',
            'new_location', 'reason', 'reason_details', 'initiated_by_type',
            'initiated_by_user', 'initiated_by_user_id', 'candidate_notified',
            'interviewers_notified', 'notification_sent_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class InterviewListSerializer(serializers.ModelSerializer):
    """Serializer for interview list view"""
    candidate_name = serializers.CharField(source='candidate.name', read_only=True)
    candidate_email = serializers.CharField(source='candidate.email', read_only=True)
    mpr_title = serializers.CharField(source='mpr.job_title.title', read_only=True)
    mpr_number = serializers.CharField(source='mpr.mpr_number', read_only=True)
    interview_round = InterviewRoundSerializer(read_only=True)
    participants_count = serializers.SerializerMethodField()
    is_upcoming = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    actual_duration_minutes = serializers.ReadOnlyField()
    
    class Meta:
        model = Interview
        fields = [
            'id', 'candidate', 'candidate_name', 'candidate_email', 'mpr',
            'mpr_title', 'mpr_number', 'interview_round', 'title',
            'scheduled_date', 'duration_minutes', 'location', 'status',
            'overall_score', 'recommendation', 'participants_count',
            'is_upcoming', 'is_overdue', 'actual_duration_minutes',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_participants_count(self, obj):
        """Get the number of participants"""
        return obj.participants.count()


class InterviewDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for interview"""
    candidate_name = serializers.CharField(source='candidate.name', read_only=True)
    candidate_email = serializers.CharField(source='candidate.email', read_only=True)
    mpr_title = serializers.CharField(source='mpr.job_title.title', read_only=True)
    mpr_number = serializers.CharField(source='mpr.mpr_number', read_only=True)
    interview_round = InterviewRoundSerializer(read_only=True)
    participants = InterviewParticipantSerializer(many=True, read_only=True)
    criteria_evaluations = InterviewCriteriaEvaluationSerializer(many=True, read_only=True)
    question_responses = InterviewQuestionResponseSerializer(many=True, read_only=True)
    reschedule_history = InterviewRescheduleSerializer(many=True, read_only=True)
    created_by = UserBasicSerializer(read_only=True)
    
    # Computed fields
    is_upcoming = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    actual_duration_minutes = serializers.ReadOnlyField()
    can_be_rescheduled = serializers.SerializerMethodField()
    can_be_cancelled = serializers.SerializerMethodField()
    
    class Meta:
        model = Interview
        fields = [
            'id', 'candidate', 'candidate_name', 'candidate_email', 'mpr',
            'mpr_title', 'mpr_number', 'interview_round', 'title',
            'scheduled_date', 'duration_minutes', 'location', 'meeting_link',
            'meeting_details', 'status', 'actual_start_time', 'actual_end_time',
            'overall_score', 'strengths', 'weaknesses', 'general_feedback',
            'recommendation', 'interviewer_notes', 'preparation_notes',
            'created_at', 'updated_at', 'created_by', 'participants',
            'criteria_evaluations', 'question_responses', 'reschedule_history',
            'is_upcoming', 'is_overdue', 'actual_duration_minutes',
            'can_be_rescheduled', 'can_be_cancelled'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_can_be_rescheduled(self, obj):
        """Check if interview can be rescheduled"""
        return obj.can_be_rescheduled()
    
    def get_can_be_cancelled(self, obj):
        """Check if interview can be cancelled"""
        return obj.can_be_cancelled()


class InterviewCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating interviews"""
    participants_data = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        help_text="List of participant data with user_id and role"
    )
    
    class Meta:
        model = Interview
        fields = [
            'candidate', 'mpr', 'interview_round', 'title', 'scheduled_date',
            'duration_minutes', 'location', 'meeting_link', 'meeting_details',
            'status', 'actual_start_time', 'actual_end_time', 'overall_score',
            'strengths', 'weaknesses', 'general_feedback', 'recommendation',
            'interviewer_notes', 'preparation_notes', 'participants_data'
        ]
    
    def validate_overall_score(self, value):
        """Validate overall score range"""
        if value is not None and (value < 0.0 or value > 5.0):
            raise serializers.ValidationError("Overall score must be between 0.0 and 5.0.")
        return value
    
    def validate_scheduled_date(self, value):
        """Validate scheduled date is in the future for new interviews"""
        if value and not self.instance and value < timezone.now():
            raise serializers.ValidationError("Scheduled date must be in the future.")
        return value
    
    def validate_actual_times(self, attrs):
        """Validate actual start and end times"""
        start_time = attrs.get('actual_start_time')
        end_time = attrs.get('actual_end_time')
        
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError(
                "Actual end time must be after actual start time."
            )
        
        return attrs
    
    def validate(self, attrs):
        """Custom validation"""
        attrs = self.validate_actual_times(attrs)
        return attrs
    
    def create(self, validated_data):
        """Create interview with participants"""
        participants_data = validated_data.pop('participants_data', [])
        
        interview = Interview.objects.create(
            created_by=self.context.get('request').user if self.context.get('request') else None,
            **validated_data
        )
        
        # Create participants
        for participant_data in participants_data:
            InterviewParticipant.objects.create(
                interview=interview,
                **participant_data
            )
        
        return interview
    
    def update(self, instance, validated_data):
        """Update interview"""
        participants_data = validated_data.pop('participants_data', None)
        
        # Update interview fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update participants if provided
        if participants_data is not None:
            # Delete existing participants
            instance.participants.all().delete()
            
            # Create new participants
            for participant_data in participants_data:
                InterviewParticipant.objects.create(
                    interview=instance,
                    **participant_data
                )
        
        return instance


class InterviewFeedbackTemplateSerializer(serializers.ModelSerializer):
    """Serializer for interview feedback templates"""
    interview_round = InterviewRoundSerializer(read_only=True)
    interview_round_id = serializers.IntegerField(write_only=True)
    created_by = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = InterviewFeedbackTemplate
        fields = [
            'id', 'interview_round', 'interview_round_id', 'name',
            'description', 'sections', 'is_default', 'is_active',
            'created_at', 'updated_at', 'created_by'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_sections(self, value):
        """Validate sections structure"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Sections must be a list.")
        
        for section in value:
            if not isinstance(section, dict):
                raise serializers.ValidationError("Each section must be a dictionary.")
            
            required_fields = ['name', 'weight', 'fields']
            for field in required_fields:
                if field not in section:
                    raise serializers.ValidationError(f"Section must contain '{field}' field.")
            
            # Validate weight
            weight = section.get('weight')
            if not isinstance(weight, (int, float)) or weight < 0 or weight > 1:
                raise serializers.ValidationError("Section weight must be between 0 and 1.")
            
            # Validate fields
            fields = section.get('fields')
            if not isinstance(fields, list):
                raise serializers.ValidationError("Section fields must be a list.")
            
            for field in fields:
                if not isinstance(field, dict):
                    raise serializers.ValidationError("Each field must be a dictionary.")
                
                field_required = ['name', 'type']
                for req_field in field_required:
                    if req_field not in field:
                        raise serializers.ValidationError(f"Field must contain '{req_field}'.")
        
        return value


class InterviewCalendarIntegrationSerializer(serializers.ModelSerializer):
    """Serializer for calendar integration"""
    
    class Meta:
        model = InterviewCalendarIntegration
        fields = [
            'id', 'google_event_id', 'outlook_event_id', 'is_synced',
            'last_sync_at', 'sync_errors', 'calendar_invite_sent',
            'reminder_set', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# Additional serializers for specific actions

class InterviewRescheduleCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating interview reschedules"""
    
    class Meta:
        model = InterviewReschedule
        fields = [
            'new_date', 'new_location', 'reason', 'reason_details',
            'initiated_by_type'
        ]
    
    def create(self, validated_data):
        """Create reschedule record and update interview"""
        interview = self.context['interview']
        
        # Create reschedule record
        reschedule = InterviewReschedule.objects.create(
            interview=interview,
            previous_date=interview.scheduled_date,
            previous_location=interview.location,
            initiated_by_user=self.context.get('request').user if self.context.get('request') else None,
            **validated_data
        )
        
        # Update interview
        interview.scheduled_date = validated_data['new_date']
        interview.location = validated_data.get('new_location', interview.location)
        interview.status = 'rescheduled'
        interview.save(update_fields=['scheduled_date', 'location', 'status'])
        
        return reschedule


class InterviewStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating interview status"""
    status = serializers.ChoiceField(choices=Interview.STATUS_CHOICES)
    reason = serializers.CharField(required=False, allow_blank=True)
    actual_start_time = serializers.DateTimeField(required=False, allow_null=True)
    actual_end_time = serializers.DateTimeField(required=False, allow_null=True)
    
    def validate(self, attrs):
        """Validate status update"""
        status = attrs.get('status')
        start_time = attrs.get('actual_start_time')
        end_time = attrs.get('actual_end_time')
        
        # Validate that completed interviews have actual times
        if status == 'completed':
            if not start_time or not end_time:
                raise serializers.ValidationError(
                    "Completed interviews must have actual start and end times."
                )
            
            if start_time >= end_time:
                raise serializers.ValidationError(
                    "Actual end time must be after actual start time."
                )
        
        return attrs


class InterviewParticipantFeedbackSerializer(serializers.Serializer):
    """Serializer for participant feedback submission"""
    individual_score = serializers.DecimalField(
        max_digits=3, 
        decimal_places=1, 
        min_value=0.0, 
        max_value=5.0,
        required=False,
        allow_null=True
    )
    individual_feedback = serializers.CharField(required=False, allow_blank=True)
    individual_recommendation = serializers.ChoiceField(
        choices=Interview.RECOMMENDATION_CHOICES,
        required=False,
        allow_null=True
    )
    criteria_evaluations = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="List of criteria evaluations with criteria_name, score, comments, weight"
    )
    
    def validate_criteria_evaluations(self, value):
        """Validate criteria evaluations structure"""
        for evaluation in value:
            if 'criteria_name' not in evaluation:
                raise serializers.ValidationError("Each evaluation must have criteria_name.")
            
            if 'score' not in evaluation:
                raise serializers.ValidationError("Each evaluation must have score.")
            
            score = evaluation['score']
            if not isinstance(score, (int, float)) or score < 0 or score > 5:
                raise serializers.ValidationError("Score must be between 0 and 5.")
        
        return value