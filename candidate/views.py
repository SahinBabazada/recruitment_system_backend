from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
from django.shortcuts import get_object_or_404
from django.http import Http404

from .models import (
    Candidate, CandidateStatusUpdate, CandidateEmail, 
    EmailAttachment, CandidateMPR
)
from .serializers import (
    CandidateListSerializer, CandidateDetailSerializer,
    CandidateCreateUpdateSerializer, CandidateEmailSerializer,
    CandidateEmailCreateSerializer, EmailAttachmentSerializer,
    EmailAttachmentUploadSerializer, CandidateMPRSerializer,
    CandidateMPRCreateUpdateSerializer, CandidateStatusUpdateSerializer
)
from .filters import CandidateFilter


class CandidateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing candidates
    
    Provides CRUD operations for candidates with filtering, searching, and custom actions
    """
    queryset = Candidate.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CandidateFilter
    search_fields = ['name', 'email', 'current_position', 'current_company']
    ordering_fields = ['name', 'applied_at', 'overall_score', 'skill_match_percentage']
    ordering = ['-applied_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return CandidateListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return CandidateCreateUpdateSerializer
        else:
            return CandidateDetailSerializer
    
    def get_queryset(self):
        """Optimize queryset based on action"""
        queryset = Candidate.objects.all()
        
        if self.action == 'list':
            # Optimize for list view
            queryset = queryset.select_related().prefetch_related(
                'status_updates__updated_by',
                'interviews',
                'emails',
                'attachments',
                'mpr_applications'
            )
        elif self.action == 'retrieve':
            # Optimize for detail view
            queryset = queryset.select_related().prefetch_related(
                'status_updates__updated_by',
                'emails__attachments',
                'attachments',
                'mpr_applications__mpr__job_title',
                'mpr_applications__primary_cv',
                'mpr_applications__updated_by',
                'interviews'
            )
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update candidate hiring status"""
        candidate = self.get_object()
        new_status = request.data.get('status')
        reason = request.data.get('reason', '')
        
        if not new_status:
            return Response(
                {'error': 'Status is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_status not in dict(Candidate.HIRING_STATUS_CHOICES):
            return Response(
                {'error': 'Invalid status'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_status = candidate.hiring_status
        candidate.hiring_status = new_status
        candidate.save(update_fields=['hiring_status'])
        
        # Create status update record
        status_update = CandidateStatusUpdate.objects.create(
            candidate=candidate,
            previous_status=old_status,
            new_status=new_status,
            reason=reason,
            updated_by=request.user
        )
        
        return Response({
            'message': 'Status updated successfully',
            'status_update': CandidateStatusUpdateSerializer(status_update).data
        })
    
    @action(detail=True, methods=['post'])
    def calculate_scores(self, request, pk=None):
        """Recalculate candidate scores"""
        candidate = self.get_object()
        overall_score = candidate.calculate_overall_score()
        
        if overall_score is not None:
            candidate.save(update_fields=['overall_score'])
            return Response({
                'message': 'Scores calculated successfully',
                'overall_score': overall_score
            })
        else:
            return Response({
                'message': 'No individual scores available to calculate overall score',
                'overall_score': None
            })
    
    @action(detail=True, methods=['post'])
    def update_skill_matching(self, request, pk=None):
        """Update skill matching for candidate"""
        candidate = self.get_object()
        required_skills = request.data.get('required_skills', [])
        candidate_skills = request.data.get('candidate_skills', [])
        
        if not required_skills:
            return Response(
                {'error': 'Required skills list is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        candidate.update_skill_matching(required_skills, candidate_skills)
        candidate.save(update_fields=['skill_match_percentage', 'matched_skills_count', 'total_skills_count'])
        
        return Response({
            'message': 'Skill matching updated successfully',
            'skill_match_percentage': candidate.skill_match_percentage,
            'matched_skills_count': candidate.matched_skills_count,
            'total_skills_count': candidate.total_skills_count
        })
    
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get dashboard statistics for candidates"""
        total_candidates = Candidate.objects.count()
        
        # Status distribution
        status_stats = {}
        for status_choice, label in Candidate.HIRING_STATUS_CHOICES:
            count = Candidate.objects.filter(hiring_status=status_choice).count()
            status_stats[status_choice] = {
                'label': label,
                'count': count,
                'percentage': round((count / total_candidates * 100), 2) if total_candidates > 0 else 0
            }
        
        # Score statistics
        score_stats = Candidate.objects.exclude(overall_score__isnull=True).aggregate(
            avg_score=Avg('overall_score'),
            count_scored=Count('id')
        )
        
        # Recent activity
        recent_candidates = Candidate.objects.filter(
            applied_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        return Response({
            'total_candidates': total_candidates,
            'status_distribution': status_stats,
            'average_score': score_stats['avg_score'],
            'candidates_with_scores': score_stats['count_scored'],
            'recent_candidates_30_days': recent_candidates
        })
    
    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        """Get candidate timeline (status updates, interviews, emails)"""
        candidate = self.get_object()
        
        timeline_events = []
        
        # Add status updates
        for update in candidate.status_updates.all():
            timeline_events.append({
                'type': 'status_update',
                'date': update.updated_at,
                'title': f"Status changed to {update.get_new_status_display()}",
                'description': update.reason,
                'user': update.updated_by.get_full_name() if update.updated_by else None,
                'data': CandidateStatusUpdateSerializer(update).data
            })
        
        # Add interviews (from related interview app)
        for interview in candidate.interviews.all():
            timeline_events.append({
                'type': 'interview',
                'date': interview.scheduled_date or interview.created_at,
                'title': f"Interview: {interview.interview_round.name}",
                'description': f"Status: {interview.get_status_display()}",
                'user': interview.created_by.get_full_name() if interview.created_by else None,
                'data': {
                    'id': interview.id,
                    'status': interview.status,
                    'round_name': interview.interview_round.name,
                    'scheduled_date': interview.scheduled_date,
                    'location': interview.location
                }
            })
        
        # Add important emails
        for email in candidate.emails.filter(email_type__in=['application', 'interview_invitation', 'offer_letter']):
            timeline_events.append({
                'type': 'email',
                'date': email.sent_at,
                'title': f"Email: {email.subject}",
                'description': f"Type: {email.get_email_type_display()}",
                'user': email.from_email if not email.is_inbound else email.to_email,
                'data': {
                    'id': email.id,
                    'subject': email.subject,
                    'email_type': email.email_type,
                    'is_inbound': email.is_inbound
                }
            })
        
        # Sort by date (most recent first)
        timeline_events.sort(key=lambda x: x['date'], reverse=True)
        
        return Response({
            'candidate': candidate.name,
            'timeline': timeline_events
        })


class CandidateEmailViewSet(viewsets.ModelViewSet):
    """ViewSet for managing candidate emails"""
    serializer_class = CandidateEmailSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['email_type', 'is_inbound', 'is_read']
    search_fields = ['subject', 'body', 'from_email', 'to_email']
    ordering_fields = ['sent_at', 'received_at']
    ordering = ['-sent_at']
    
    def get_queryset(self):
        """Filter emails by candidate"""
        candidate_id = self.kwargs.get('candidate_pk')
        if candidate_id:
            return CandidateEmail.objects.filter(candidate_id=candidate_id).prefetch_related('attachments')
        return CandidateEmail.objects.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action in ['create', 'update', 'partial_update']:
            return CandidateEmailCreateSerializer
        return CandidateEmailSerializer
    
    def get_serializer_context(self):
        """Add candidate to serializer context"""
        context = super().get_serializer_context()
        candidate_id = self.kwargs.get('candidate_pk')
        if candidate_id:
            context['candidate'] = get_object_or_404(Candidate, pk=candidate_id)
        return context
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, candidate_pk=None, pk=None):
        """Mark email as read"""
        email = self.get_object()
        email.is_read = True
        email.save(update_fields=['is_read'])
        
        return Response({'message': 'Email marked as read'})
    
    @action(detail=True, methods=['post'])
    def mark_unread(self, request, candidate_pk=None, pk=None):
        """Mark email as unread"""
        email = self.get_object()
        email.is_read = False
        email.save(update_fields=['is_read'])
        
        return Response({'message': 'Email marked as unread'})


class EmailAttachmentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing email attachments"""
    serializer_class = EmailAttachmentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['file_type', 'is_visible_to_line_manager', 'is_primary_cv']
    search_fields = ['original_file_name', 'file_name']
    ordering_fields = ['uploaded_at', 'file_size']
    ordering = ['-uploaded_at']
    
    def get_queryset(self):
        """Filter attachments by candidate and optionally by email"""
        candidate_id = self.kwargs.get('candidate_pk')
        email_id = self.kwargs.get('email_pk')
        
        if candidate_id:
            queryset = EmailAttachment.objects.filter(candidate_id=candidate_id)
            if email_id:
                queryset = queryset.filter(email_id=email_id)
            return queryset.select_related('candidate', 'email')
        return EmailAttachment.objects.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action in ['create', 'update', 'partial_update']:
            return EmailAttachmentUploadSerializer
        return EmailAttachmentSerializer
    
    def get_serializer_context(self):
        """Add candidate and email to serializer context"""
        context = super().get_serializer_context()
        candidate_id = self.kwargs.get('candidate_pk')
        email_id = self.kwargs.get('email_pk')
        
        if candidate_id:
            context['candidate'] = get_object_or_404(Candidate, pk=candidate_id)
        if email_id:
            context['email'] = get_object_or_404(CandidateEmail, pk=email_id)
        
        return context
    
    @action(detail=True, methods=['post'])
    def set_primary_cv(self, request, candidate_pk=None, pk=None):
        """Set this attachment as primary CV"""
        attachment = self.get_object()
        
        # Remove primary CV flag from other attachments for this candidate
        EmailAttachment.objects.filter(
            candidate_id=candidate_pk, 
            is_primary_cv=True
        ).update(is_primary_cv=False)
        
        # Set this attachment as primary CV
        attachment.is_primary_cv = True
        attachment.is_visible_to_line_manager = True
        attachment.save(update_fields=['is_primary_cv', 'is_visible_to_line_manager'])
        
        return Response({'message': 'Attachment set as primary CV'})
    
    @action(detail=True, methods=['post'])
    def toggle_visibility(self, request, candidate_pk=None, pk=None):
        """Toggle visibility to line managers"""
        attachment = self.get_object()
        attachment.is_visible_to_line_manager = not attachment.is_visible_to_line_manager
        attachment.save(update_fields=['is_visible_to_line_manager'])
        
        return Response({
            'message': 'Visibility updated',
            'is_visible_to_line_manager': attachment.is_visible_to_line_manager
        })
    
    @action(detail=False, methods=['get'])
    def by_type(self, request, candidate_pk=None):
        """Get attachments grouped by type"""
        attachments = self.get_queryset()
        
        grouped = {}
        for attachment in attachments:
            file_type = attachment.file_type
            if file_type not in grouped:
                grouped[file_type] = []
            grouped[file_type].append(EmailAttachmentSerializer(attachment, context={'request': request}).data)
        
        return Response(grouped)


class CandidateMPRViewSet(viewsets.ModelViewSet):
    """ViewSet for managing candidate MPR relationships"""
    serializer_class = CandidateMPRSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['application_stage', 'mpr__status']
    ordering_fields = ['applied_at', 'updated_at']
    ordering = ['-applied_at']
    
    def get_queryset(self):
        """Filter by candidate"""
        candidate_id = self.kwargs.get('candidate_pk')
        if candidate_id:
            return CandidateMPR.objects.filter(
                candidate_id=candidate_id
            ).select_related(
                'mpr__job_title', 'primary_cv', 'updated_by'
            )
        return CandidateMPR.objects.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action in ['create', 'update', 'partial_update']:
            return CandidateMPRCreateUpdateSerializer
        return CandidateMPRSerializer
    
    def get_serializer_context(self):
        """Add candidate to serializer context"""
        context = super().get_serializer_context()
        candidate_id = self.kwargs.get('candidate_pk')
        if candidate_id:
            context['candidate'] = get_object_or_404(Candidate, pk=candidate_id)
        return context
    
    @action(detail=True, methods=['post'])
    def update_stage(self, request, candidate_pk=None, pk=None):
        """Update application stage"""
        application = self.get_object()
        new_stage = request.data.get('stage')
        
        if not new_stage:
            return Response(
                {'error': 'Stage is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        valid_stages = [choice[0] for choice in CandidateMPR._meta.get_field('application_stage').choices]
        if new_stage not in valid_stages:
            return Response(
                {'error': 'Invalid stage'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        application.application_stage = new_stage
        application.updated_by = request.user
        application.save(update_fields=['application_stage', 'updated_by', 'updated_at'])
        
        return Response({
            'message': 'Application stage updated successfully',
            'application': CandidateMPRSerializer(application).data
        })
    
    @action(detail=True, methods=['post'])
    def set_primary_cv(self, request, candidate_pk=None, pk=None):
        """Set primary CV for this MPR application"""
        application = self.get_object()
        attachment_id = request.data.get('attachment_id')
        
        if not attachment_id:
            return Response(
                {'error': 'Attachment ID is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            attachment = EmailAttachment.objects.get(
                id=attachment_id, 
                candidate_id=candidate_pk
            )
        except EmailAttachment.DoesNotExist:
            return Response(
                {'error': 'Attachment not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        application.primary_cv = attachment
        application.updated_by = request.user
        application.save(update_fields=['primary_cv', 'updated_by', 'updated_at'])
        
        # Ensure the attachment is visible to line managers
        attachment.is_visible_to_line_manager = True
        attachment.save(update_fields=['is_visible_to_line_manager'])
        
        return Response({
            'message': 'Primary CV set successfully',
            'primary_cv': EmailAttachmentSerializer(attachment, context={'request': request}).data
        })


# Additional imports needed
from django.utils import timezone
from datetime import timedelta
from .filters import CandidateFilter