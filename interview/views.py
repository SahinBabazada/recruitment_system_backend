from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg, F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta, datetime

from .models import (
    InterviewRound, Interview, InterviewParticipant, 
    InterviewCriteriaEvaluation, InterviewQuestion,
    InterviewQuestionResponse, InterviewReschedule,
    InterviewFeedbackTemplate, InterviewCalendarIntegration
)
from .serializers import (
    InterviewRoundSerializer, InterviewListSerializer, InterviewDetailSerializer,
    InterviewCreateUpdateSerializer, InterviewParticipantSerializer,
    InterviewCriteriaEvaluationSerializer, InterviewQuestionSerializer,
    InterviewQuestionResponseSerializer, InterviewRescheduleSerializer,
    InterviewRescheduleCreateSerializer, InterviewFeedbackTemplateSerializer,
    InterviewCalendarIntegrationSerializer, InterviewStatusUpdateSerializer,
    InterviewParticipantFeedbackSerializer
)
from .filters import InterviewFilter, InterviewParticipantFilter


class InterviewRoundViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing interview rounds
    """
    queryset = InterviewRound.objects.all()
    serializer_class = InterviewRoundSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'sequence_order']
    search_fields = ['name', 'description']
    ordering_fields = ['sequence_order', 'name', 'created_at']
    ordering = ['sequence_order']
    
    def get_queryset(self):
        """Optimize queryset"""
        return InterviewRound.objects.prefetch_related('interviews', 'standard_questions')
    
    @action(detail=True, methods=['get'])
    def questions(self, request, pk=None):
        """Get questions for this interview round"""
        interview_round = self.get_object()
        questions = interview_round.standard_questions.filter(is_active=True)
        
        serializer = InterviewQuestionSerializer(questions, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def feedback_templates(self, request, pk=None):
        """Get feedback templates for this interview round"""
        interview_round = self.get_object()
        templates = interview_round.feedback_templates.filter(is_active=True)
        
        serializer = InterviewFeedbackTemplateSerializer(templates, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get statistics for this interview round"""
        interview_round = self.get_object()
        interviews = interview_round.interviews.all()
        
        total_interviews = interviews.count()
        completed_interviews = interviews.filter(status='completed')
        
        stats = {
            'total_interviews': total_interviews,
            'completed_interviews': completed_interviews.count(),
            'average_score': completed_interviews.aggregate(avg=Avg('overall_score'))['avg'],
            'status_distribution': {}
        }
        
        # Status distribution
        for status_choice, label in Interview.STATUS_CHOICES:
            count = interviews.filter(status=status_choice).count()
            stats['status_distribution'][status_choice] = {
                'label': label,
                'count': count,
                'percentage': round((count / total_interviews * 100), 2) if total_interviews > 0 else 0
            }
        
        return Response(stats)


class InterviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing interviews
    """
    queryset = Interview.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = InterviewFilter
    search_fields = ['title', 'candidate__name', 'candidate__email', 'mpr__job_title__title']
    ordering_fields = ['scheduled_date', 'created_at', 'overall_score']
    ordering = ['-scheduled_date']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return InterviewListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return InterviewCreateUpdateSerializer
        else:
            return InterviewDetailSerializer
    
    def get_queryset(self):
        """Optimize queryset based on action"""
        queryset = Interview.objects.all()
        
        if self.action == 'list':
            queryset = queryset.select_related(
                'candidate', 'mpr__job_title', 'interview_round', 'created_by'
            ).prefetch_related('participants')
        elif self.action == 'retrieve':
            queryset = queryset.select_related(
                'candidate', 'mpr__job_title', 'interview_round', 'created_by'
            ).prefetch_related(
                'participants__user',
                'criteria_evaluations__participant__user',
                'question_responses__question__interview_round',
                'question_responses__asked_by__user',
                'reschedule_history__initiated_by_user'
            )
        
        return queryset
        
    #Add this action to your InterviewViewSet in views.py
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get dashboard statistics for interviews"""
        from django.db.models import Count, Avg, Q
        from django.utils import timezone
        from datetime import timedelta
        
        # Get date ranges
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Base queryset
        interviews = Interview.objects.all()
        
        # Basic counts
        total_interviews = interviews.count()
        completed_interviews = interviews.filter(status='completed').count()
        upcoming_interviews = interviews.filter(
            scheduled_date__gte=timezone.now(),
            status__in=['scheduled', 'confirmed']
        ).count()
        
        # Recent activity
        recent_interviews = interviews.filter(
            created_at__gte=week_ago
        ).count()
        
        # Status distribution
        status_distribution = {}
        for status_choice, label in Interview.STATUS_CHOICES:
            count = interviews.filter(status=status_choice).count()
            status_distribution[status_choice] = {
                'label': label,
                'count': count,
                'percentage': round((count / total_interviews * 100), 2) if total_interviews > 0 else 0
            }
        
        # Recommendation distribution (for completed interviews)
        recommendation_distribution = {}
        completed = interviews.filter(status='completed')
        completed_count = completed.count()
        
        if completed_count > 0:
            for rec_choice, label in Interview.RECOMMENDATION_CHOICES:
                count = completed.filter(recommendation=rec_choice).count()
                recommendation_distribution[rec_choice] = {
                    'label': label,
                    'count': count,
                    'percentage': round((count / completed_count * 100), 2) if completed_count > 0 else 0
                }
        
        # Average scores
        avg_score = completed.aggregate(avg=Avg('overall_score'))['avg']
        
        # Interviews by round
        round_stats = interviews.values(
            'interview_round__name'
        ).annotate(
            count=Count('id'),
            completed=Count('id', filter=Q(status='completed')),
            avg_score=Avg('overall_score', filter=Q(status='completed'))
        ).order_by('-count')
        
        # This week's activity
        this_week = interviews.filter(
            scheduled_date__gte=week_ago,
            scheduled_date__lte=today + timedelta(days=1)
        )
        
        week_stats = {
            'scheduled': this_week.filter(status__in=['scheduled', 'confirmed']).count(),
            'completed': this_week.filter(status='completed').count(),
            'cancelled': this_week.filter(status='cancelled').count(),
        }
        
        stats = {
            'total_interviews': total_interviews,
            'completed_interviews': completed_interviews,
            'upcoming_interviews': upcoming_interviews,
            'recent_interviews': recent_interviews,
            'completion_rate': round((completed_interviews / total_interviews * 100), 2) if total_interviews > 0 else 0,
            'average_score': round(avg_score, 2) if avg_score else None,
            'status_distribution': status_distribution,
            'recommendation_distribution': recommendation_distribution,
            'round_statistics': list(round_stats),
            'week_activity': week_stats,
            'generated_at': timezone.now()
        }
        
        return Response(stats)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update interview status"""
        interview = self.get_object()
        serializer = InterviewStatusUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            old_status = interview.status
            new_status = serializer.validated_data['status']
            
            interview.status = new_status
            
            # Update actual times if provided
            if 'actual_start_time' in serializer.validated_data:
                interview.actual_start_time = serializer.validated_data['actual_start_time']
            if 'actual_end_time' in serializer.validated_data:
                interview.actual_end_time = serializer.validated_data['actual_end_time']
            
            interview.save()
            
            return Response({
                'message': f'Interview status updated from {old_status} to {new_status}',
                'interview': InterviewDetailSerializer(interview, context={'request': request}).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def reschedule(self, request, pk=None):
        """Reschedule interview"""
        interview = self.get_object()
        
        if not interview.can_be_rescheduled():
            return Response(
                {'error': 'Interview cannot be rescheduled in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = InterviewRescheduleCreateSerializer(
            data=request.data,
            context={'interview': interview, 'request': request}
        )
        
        if serializer.is_valid():
            reschedule = serializer.save()
            return Response({
                'message': 'Interview rescheduled successfully',
                'reschedule': InterviewRescheduleSerializer(reschedule).data,
                'interview': InterviewDetailSerializer(interview, context={'request': request}).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel interview"""
        interview = self.get_object()
        
        if not interview.can_be_cancelled():
            return Response(
                {'error': 'Interview cannot be cancelled in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reason = request.data.get('reason', '')
        interview.status = 'cancelled'
        interview.save(update_fields=['status'])
        
        return Response({
            'message': 'Interview cancelled successfully',
            'interview': InterviewDetailSerializer(interview, context={'request': request}).data
        })
    
    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        """Add participant to interview"""
        interview = self.get_object()
        
        serializer = InterviewParticipantSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            participant = serializer.save(interview=interview)
            return Response({
                'message': 'Participant added successfully',
                'participant': InterviewParticipantSerializer(participant).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def submit_feedback(self, request, pk=None):
        """Submit feedback for interview (for participants)"""
        interview = self.get_object()
        user = request.user
        
        # Get or create participant record for this user
        try:
            participant = interview.participants.get(user=user)
        except InterviewParticipant.DoesNotExist:
            return Response(
                {'error': 'User is not a participant in this interview'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = InterviewParticipantFeedbackSerializer(data=request.data)
        
        if serializer.is_valid():
            data = serializer.validated_data
            
            # Update participant feedback
            if 'individual_score' in data:
                participant.individual_score = data['individual_score']
            if 'individual_feedback' in data:
                participant.individual_feedback = data['individual_feedback']
            if 'individual_recommendation' in data:
                participant.individual_recommendation = data['individual_recommendation']
            
            participant.save()
            
            # Update criteria evaluations
            if 'criteria_evaluations' in data:
                # Delete existing evaluations for this participant
                interview.criteria_evaluations.filter(participant=participant).delete()
                
                # Create new evaluations
                for eval_data in data['criteria_evaluations']:
                    InterviewCriteriaEvaluation.objects.create(
                        interview=interview,
                        participant=participant,
                        criteria_name=eval_data['criteria_name'],
                        score=eval_data['score'],
                        comments=eval_data.get('comments', ''),
                        weight=eval_data.get('weight', 1.0)
                    )
            
            return Response({
                'message': 'Feedback submitted successfully',
                'participant': InterviewParticipantSerializer(participant).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def feedback_summary(self, request, pk=None):
        """Get feedback summary for interview"""
        interview = self.get_object()
        
        # Participant feedback
        participants_with_feedback = interview.participants.filter(
            individual_score__isnull=False
        )
        
        # Criteria evaluations
        criteria_evals = interview.criteria_evaluations.all()
        
        # Calculate averages
        avg_individual_score = participants_with_feedback.aggregate(
            avg=Avg('individual_score')
        )['avg']
        
        # Group criteria evaluations
        criteria_summary = {}
        for eval in criteria_evals:
            criteria_name = eval.criteria_name
            if criteria_name not in criteria_summary:
                criteria_summary[criteria_name] = {
                    'scores': [],
                    'comments': [],
                    'weights': []
                }
            
            criteria_summary[criteria_name]['scores'].append(float(eval.score))
            if eval.comments:
                criteria_summary[criteria_name]['comments'].append(eval.comments)
            criteria_summary[criteria_name]['weights'].append(float(eval.weight))
        
        # Calculate criteria averages
        for criteria_name, data in criteria_summary.items():
            scores = data['scores']
            weights = data['weights']
            
            if scores:
                # Weighted average
                weighted_sum = sum(score * weight for score, weight in zip(scores, weights))
                total_weight = sum(weights)
                data['average_score'] = weighted_sum / total_weight if total_weight > 0 else 0
                data['count'] = len(scores)
        
        # Recommendations distribution
        recommendations = participants_with_feedback.values_list('individual_recommendation', flat=True)
        recommendation_counts = {}
        for rec in recommendations:
            if rec:
                recommendation_counts[rec] = recommendation_counts.get(rec, 0) + 1
        
        return Response({
            'overall_score': interview.overall_score,
            'average_individual_score': avg_individual_score,
            'participants_count': interview.participants.count(),
            'participants_with_feedback': participants_with_feedback.count(),
            'criteria_summary': criteria_summary,
            'recommendation_distribution': recommendation_counts,
            'general_feedback': interview.general_feedback,
            'strengths': interview.strengths,
            'weaknesses': interview.weaknesses,
            'recommendation': interview.recommendation
        })
    
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get dashboard statistics for interviews"""
        total_interviews = Interview.objects.count()
        
        # Today's interviews
        today = timezone.now().date()
        today_interviews = Interview.objects.filter(
            scheduled_date__date=today
        ).count()
        
        # This week's interviews
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        week_interviews = Interview.objects.filter(
            scheduled_date__date__range=[week_start, week_end]
        ).count()
        
        # Upcoming interviews
        upcoming_interviews = Interview.objects.filter(
            scheduled_date__gt=timezone.now(),
            status__in=['scheduled', 'confirmed']
        ).count()
        
        # Overdue interviews
        overdue_interviews = Interview.objects.filter(
            scheduled_date__lt=timezone.now(),
            status__in=['scheduled', 'confirmed']
        ).count()
        
        # Status distribution
        status_stats = {}
        for status_choice, label in Interview.STATUS_CHOICES:
            count = Interview.objects.filter(status=status_choice).count()
            status_stats[status_choice] = {
                'label': label,
                'count': count,
                'percentage': round((count / total_interviews * 100), 2) if total_interviews > 0 else 0
            }
        
        # Average scores
        completed_interviews = Interview.objects.filter(status='completed')
        avg_score = completed_interviews.aggregate(avg=Avg('overall_score'))['avg']
        
        return Response({
            'total_interviews': total_interviews,
            'today_interviews': today_interviews,
            'week_interviews': week_interviews,
            'upcoming_interviews': upcoming_interviews,
            'overdue_interviews': overdue_interviews,
            'status_distribution': status_stats,
            'average_score': avg_score,
            'completed_interviews': completed_interviews.count()
        })
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming interviews"""
        upcoming = Interview.objects.filter(
            scheduled_date__gt=timezone.now(),
            status__in=['scheduled', 'confirmed']
        ).select_related(
            'candidate', 'mpr__job_title', 'interview_round'
        ).order_by('scheduled_date')
        
        serializer = InterviewListSerializer(upcoming, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_interviews(self, request):
        """Get interviews where current user is a participant"""
        user_interviews = Interview.objects.filter(
            participants__user=request.user
        ).select_related(
            'candidate', 'mpr__job_title', 'interview_round'
        ).order_by('-scheduled_date')
        
        serializer = InterviewListSerializer(user_interviews, many=True, context={'request': request})
        return Response(serializer.data)


class InterviewParticipantViewSet(viewsets.ModelViewSet):
    """ViewSet for managing interview participants"""
    serializer_class = InterviewParticipantSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = InterviewParticipantFilter
    ordering_fields = ['role', 'created_at']
    ordering = ['role']
    
    def get_queryset(self):
        """Filter by interview"""
        interview_id = self.kwargs.get('interview_pk')
        if interview_id:
            return InterviewParticipant.objects.filter(
                interview_id=interview_id
            ).select_related('user', 'interview')
        return InterviewParticipant.objects.none()
    
    @action(detail=True, methods=['post'])
    def mark_attended(self, request, interview_pk=None, pk=None):
        """Mark participant as attended"""
        participant = self.get_object()
        participant.attended = True
        participant.joined_at = timezone.now()
        participant.save(update_fields=['attended', 'joined_at'])
        
        return Response({'message': 'Participant marked as attended'})
    
    @action(detail=True, methods=['post'])
    def mark_left(self, request, interview_pk=None, pk=None):
        """Mark when participant left"""
        participant = self.get_object()
        participant.left_at = timezone.now()
        participant.save(update_fields=['left_at'])
        
        return Response({'message': 'Participant left time recorded'})


class InterviewQuestionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing interview questions"""
    queryset = InterviewQuestion.objects.all()
    serializer_class = InterviewQuestionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['interview_round', 'question_type', 'difficulty_level', 'is_active']
    search_fields = ['question_text', 'ideal_answer_points', 'follow_up_questions']
    ordering_fields = ['usage_count', 'created_at', 'estimated_time_minutes']
    ordering = ['-usage_count']
    
    def get_queryset(self):
        """Optimize queryset"""
        return InterviewQuestion.objects.select_related('interview_round', 'created_by')
    
    def perform_create(self, serializer):
        """Set created_by when creating"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def increment_usage(self, request, pk=None):
        """Increment usage count for question"""
        question = self.get_object()
        question.usage_count = F('usage_count') + 1
        question.save(update_fields=['usage_count'])
        
        # Refresh from database to get updated value
        question.refresh_from_db()
        
        return Response({
            'message': 'Usage count incremented',
            'usage_count': question.usage_count
        })
    
    @action(detail=False, methods=['get'])
    def by_round(self, request):
        """Get questions grouped by interview round"""
        questions = self.get_queryset().filter(is_active=True)
        
        grouped = {}
        for question in questions:
            round_name = question.interview_round.name
            if round_name not in grouped:
                grouped[round_name] = []
            grouped[round_name].append(
                InterviewQuestionSerializer(question, context={'request': request}).data
            )
        
        return Response(grouped)


class InterviewQuestionResponseViewSet(viewsets.ModelViewSet):
    """ViewSet for managing interview question responses"""
    serializer_class = InterviewQuestionResponseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['question__question_type', 'asked_by__role']
    ordering_fields = ['created_at', 'response_score', 'time_taken_minutes']
    ordering = ['created_at']
    
    def get_queryset(self):
        """Filter by interview"""
        interview_id = self.kwargs.get('interview_pk')
        if interview_id:
            return InterviewQuestionResponse.objects.filter(
                interview_id=interview_id
            ).select_related(
                'question__interview_round', 'asked_by__user'
            )
        return InterviewQuestionResponse.objects.none()


class InterviewFeedbackTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing interview feedback templates"""
    queryset = InterviewFeedbackTemplate.objects.all()
    serializer_class = InterviewFeedbackTemplateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['interview_round', 'is_default', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Optimize queryset"""
        return InterviewFeedbackTemplate.objects.select_related('interview_round', 'created_by')
    
    def perform_create(self, serializer):
        """Set created_by when creating"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set this template as default for its interview round"""
        template = self.get_object()
        
        # Remove default flag from other templates in the same round
        InterviewFeedbackTemplate.objects.filter(
            interview_round=template.interview_round,
            is_default=True
        ).update(is_default=False)
        
        # Set this template as default
        template.is_default = True
        template.save(update_fields=['is_default'])
        
        return Response({'message': 'Template set as default'})


# Additional imports needed
from .filters import InterviewFilter, InterviewParticipantFilter