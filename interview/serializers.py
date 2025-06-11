# interview/serializers.py - COMPLETE FIXED VERSION

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import (
    InterviewRound, Interview, InterviewParticipant, 
    InterviewCriteriaEvaluation, InterviewQuestion,
    InterviewQuestionResponse, InterviewReschedule,
    InterviewFeedbackTemplate, InterviewCalendarIntegration
)

# Use the correct User model for your project
User = get_user_model()


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
    """Serializer for interview participants - SAFE VERSION"""
    user_id = serializers.IntegerField(write_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = InterviewParticipant
        fields = [
            'id', 'user_id', 'user_name', 'user_email', 'user_username', 'role', 
            'individual_score', 'individual_feedback', 'individual_recommendation', 
            'attended', 'joined_at', 'left_at', 'send_calendar_invite', 
            'send_reminders', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate_individual_score(self, value):
        """Validate individual score range"""
        if value is not None and (value < 0.0 or value > 5.0):
            raise serializers.ValidationError("Individual score must be between 0.0 and 5.0.")
        return value


class InterviewCriteriaEvaluationSerializer(serializers.ModelSerializer):
    """Serializer for criteria evaluations"""
    participant_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    participant_name = serializers.CharField(source='participant.user.get_full_name', read_only=True)
    
    class Meta:
        model = InterviewCriteriaEvaluation
        fields = [
            'id', 'participant_id', 'participant_name', 'criteria_name', 'score',
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
    interview_round_id = serializers.IntegerField(write_only=True)
    interview_round_name = serializers.CharField(source='interview_round.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    usage_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = InterviewQuestion
        fields = [
            'id', 'interview_round_id', 'interview_round_name', 'question_text',
            'question_type', 'evaluation_criteria', 'difficulty_level',
            'estimated_time_minutes', 'is_active', 'usage_count',
            'follow_up_questions', 'ideal_answer_points', 'created_at',
            'updated_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'usage_count']


class InterviewQuestionResponseSerializer(serializers.ModelSerializer):
    """Serializer for interview question responses"""
    question_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    asked_by_id = serializers.IntegerField(write_only=True)
    asked_by_name = serializers.CharField(source='asked_by.user.get_full_name', read_only=True)
    
    class Meta:
        model = InterviewQuestionResponse
        fields = [
            'id', 'question_id', 'question_text', 'custom_question_text',
            'candidate_answer', 'interviewer_notes', 'response_score',
            'time_taken_minutes', 'asked_by_id', 'asked_by_name', 'created_at'
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
    initiated_by_user_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    initiated_by_user_name = serializers.CharField(source='initiated_by_user.get_full_name', read_only=True)
    
    class Meta:
        model = InterviewReschedule
        fields = [
            'id', 'previous_date', 'previous_location', 'new_date',
            'new_location', 'reason', 'reason_details', 'initiated_by_type',
            'initiated_by_user_id', 'initiated_by_user_name', 'candidate_notified',
            'interviewers_notified', 'notification_sent_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class InterviewListSerializer(serializers.ModelSerializer):
    """Serializer for interview list view"""
    candidate_name = serializers.CharField(source='candidate.name', read_only=True)
    candidate_email = serializers.CharField(source='candidate.email', read_only=True)
    mpr_title = serializers.CharField(source='mpr.job_title.title', read_only=True)
    mpr_number = serializers.CharField(source='mpr.mpr_number', read_only=True)
    interview_round_name = serializers.CharField(source='interview_round.name', read_only=True)
    participants_count = serializers.SerializerMethodField()
    is_upcoming = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    actual_duration_minutes = serializers.ReadOnlyField()
    
    class Meta:
        model = Interview
        fields = [
            'id', 'candidate', 'candidate_name', 'candidate_email', 'mpr',
            'mpr_title', 'mpr_number', 'interview_round', 'interview_round_name',
            'title', 'scheduled_date', 'duration_minutes', 'location', 'status',
            'overall_score', 'recommendation', 'participants_count',
            'is_upcoming', 'is_overdue', 'actual_duration_minutes',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_participants_count(self, obj):
        """Get the number of participants"""
        return obj.participants.count()


class InterviewDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for interview - SAFE VERSION"""
    candidate_name = serializers.CharField(source='candidate.name', read_only=True)
    candidate_email = serializers.CharField(source='candidate.email', read_only=True)
    mpr_title = serializers.CharField(source='mpr.job_title.title', read_only=True)
    mpr_number = serializers.CharField(source='mpr.mpr_number', read_only=True)
    interview_round_name = serializers.CharField(source='interview_round.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    # Use SerializerMethodField for safe data retrieval
    participants = serializers.SerializerMethodField()
    criteria_evaluations = serializers.SerializerMethodField()
    question_responses = serializers.SerializerMethodField()
    reschedule_history = serializers.SerializerMethodField()
    
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
            'mpr_title', 'mpr_number', 'interview_round', 'interview_round_name',
            'title', 'scheduled_date', 'duration_minutes', 'location', 
            'meeting_link', 'meeting_details', 'status', 'actual_start_time', 
            'actual_end_time', 'overall_score', 'strengths', 'weaknesses', 
            'general_feedback', 'recommendation', 'interviewer_notes', 
            'preparation_notes', 'participants', 'criteria_evaluations',
            'question_responses', 'reschedule_history', 'is_upcoming', 
            'is_overdue', 'actual_duration_minutes', 'can_be_rescheduled', 
            'can_be_cancelled', 'created_at', 'updated_at', 'created_by', 
            'created_by_name'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_participants(self, obj):
        """Get participants safely"""
        participants_data = []
        for participant in obj.participants.select_related('user').all():
            participants_data.append({
                'id': participant.id,
                'user_id': participant.user.id,
                'user_name': participant.user.get_full_name(),
                'user_email': participant.user.email,
                'user_username': participant.user.username,
                'role': participant.role,
                'individual_score': float(participant.individual_score) if participant.individual_score else None,
                'individual_feedback': participant.individual_feedback,
                'individual_recommendation': participant.individual_recommendation,
                'attended': participant.attended,
                'joined_at': participant.joined_at,
                'left_at': participant.left_at,
                'send_calendar_invite': participant.send_calendar_invite,
                'send_reminders': participant.send_reminders,
                'created_at': participant.created_at,
            })
        return participants_data
    
    def get_criteria_evaluations(self, obj):
        """Get criteria evaluations safely"""
        evaluations_data = []
        for evaluation in obj.criteria_evaluations.select_related('participant__user').all():
            evaluations_data.append({
                'id': evaluation.id,
                'participant_id': evaluation.participant.id if evaluation.participant else None,
                'participant_name': evaluation.participant.user.get_full_name() if evaluation.participant else 'Consolidated',
                'criteria_name': evaluation.criteria_name,
                'score': float(evaluation.score),
                'comments': evaluation.comments,
                'weight': float(evaluation.weight),
                'created_at': evaluation.created_at,
            })
        return evaluations_data
    
    def get_question_responses(self, obj):
        """Get question responses safely"""
        responses_data = []
        for response in obj.question_responses.select_related(
            'question__interview_round', 'asked_by__user'
        ).all():
            responses_data.append({
                'id': response.id,
                'question_id': response.question.id if response.question else None,
                'question_text': response.question.question_text if response.question else None,
                'custom_question_text': response.custom_question_text,
                'candidate_answer': response.candidate_answer,
                'interviewer_notes': response.interviewer_notes,
                'response_score': float(response.response_score) if response.response_score else None,
                'time_taken_minutes': response.time_taken_minutes,
                'asked_by_id': response.asked_by.id,
                'asked_by_name': response.asked_by.user.get_full_name(),
                'created_at': response.created_at,
            })
        return responses_data
    
    def get_reschedule_history(self, obj):
        """Get reschedule history safely"""
        reschedules_data = []
        for reschedule in obj.reschedule_history.select_related('initiated_by_user').all():
            reschedules_data.append({
                'id': reschedule.id,
                'previous_date': reschedule.previous_date,
                'previous_location': reschedule.previous_location,
                'new_date': reschedule.new_date,
                'new_location': reschedule.new_location,
                'reason': reschedule.reason,
                'reason_details': reschedule.reason_details,
                'initiated_by_type': reschedule.initiated_by_type,
                'initiated_by_user_id': reschedule.initiated_by_user.id if reschedule.initiated_by_user else None,
                'initiated_by_user_name': reschedule.initiated_by_user.get_full_name() if reschedule.initiated_by_user else None,
                'candidate_notified': reschedule.candidate_notified,
                'interviewers_notified': reschedule.interviewers_notified,
                'notification_sent_at': reschedule.notification_sent_at,
                'created_at': reschedule.created_at,
            })
        return reschedules_data
    
    def get_can_be_rescheduled(self, obj):
        """Check if interview can be rescheduled"""
        return obj.can_be_rescheduled()
    
    def get_can_be_cancelled(self, obj):
        """Check if interview can be cancelled"""
        return obj.can_be_cancelled()


class InterviewCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating interviews"""
    participants_data = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Interview
        fields = [
            'id', 'candidate', 'mpr', 'interview_round', 'title',
            'scheduled_date', 'duration_minutes', 'location', 'meeting_link',
            'meeting_details', 'status', 'actual_start_time', 'actual_end_time',
            'overall_score', 'strengths', 'weaknesses', 'general_feedback',
            'recommendation', 'interviewer_notes', 'preparation_notes',
            'participants_data'
        ]
        read_only_fields = ['id']
    
    def validate_scheduled_date(self, value):
        """Validate scheduled date"""
        if value and value < timezone.now():
            raise serializers.ValidationError("Scheduled date cannot be in the past.")
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
    interview_round_id = serializers.IntegerField(write_only=True)
    interview_round_name = serializers.CharField(source='interview_round.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = InterviewFeedbackTemplate
        fields = [
            'id', 'interview_round_id', 'interview_round_name', 'name',
            'description', 'sections', 'is_default', 'is_active',
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_sections(self, value):
        """Validate sections structure"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Sections must be a list.")
        
        for section in value:
            if not isinstance(section, dict):
                raise serializers.ValidationError("Each section must be a dictionary.")
            
            required_fields = ['name', 'fields']
            for field in required_fields:
                if field not in section:
                    raise serializers.ValidationError(f"Section must contain '{field}'.")
            
            # Validate fields within section
            fields = section.get('fields', [])
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
        
        # Validate time sequence
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError(
                "End time must be after start time."
            )
        
        return attrs


class InterviewParticipantFeedbackSerializer(serializers.ModelSerializer):
    """Serializer for participant feedback submission"""
    
    class Meta:
        model = InterviewParticipant
        fields = [
            'individual_score', 'individual_feedback', 'individual_recommendation'
        ]
    
    def validate_individual_score(self, value):
        """Validate individual score range"""
        if value is not None and (value < 0.0 or value > 5.0):
            raise serializers.ValidationError("Individual score must be between 0.0 and 5.0.")
        return value