# candidate/views.py
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q, Count, Prefetch
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model

from .models import (
    Candidate, CandidateWorkExperience, CandidateEducation,
    CandidateProject, CandidateReference, CandidateEmailConnection,
    CandidateAttachment, CandidateStatusUpdate, CandidateMPR
)
from .serializers import (
    CandidateListSerializer, CandidateDetailSerializer, CandidateCreateUpdateSerializer,
    CandidateWorkExperienceSerializer, CandidateEducationSerializer,
    CandidateProjectSerializer, CandidateReferenceSerializer,
    CandidateEmailConnectionSerializer, CandidateAttachmentSerializer,
    CandidateStatusUpdateSerializer, CandidateMPRSerializer
)
from .filters import CandidateFilter, CandidateMPRFilter
from .utils.email_integration import EmailSyncService

User = get_user_model()


class CandidateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing candidates"""
    
    queryset = Candidate.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_class = CandidateFilter
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CandidateListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return CandidateCreateUpdateSerializer
        else:
            return CandidateDetailSerializer
    
    def get_queryset(self):
        queryset = Candidate.objects.select_related().prefetch_related(
            'work_experiences',
            'education_history',
            'projects',
            'references',
            'email_connections__email_message',
            'attachments',
            'status_updates',
            'mpr_applications__mpr'
        )
        
        # Add annotations for counts
        queryset = queryset.annotate(
            work_experiences_count=Count('work_experiences'),
            education_count=Count('education_history'),
            projects_count=Count('projects'),
            attachments_count=Count('attachments'),
            emails_count=Count('email_connections'),
            applications_count=Count('mpr_applications')
        )
        
        return queryset

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get candidate statistics"""
        from django.db.models import Avg, Count
        
        candidates = Candidate.objects.all()
        total_candidates = candidates.count()
        
        # Status distribution
        status_distribution = []
        for status_code, status_label in Candidate.HIRING_STATUS_CHOICES:
            count = candidates.filter(hiring_status=status_code).count()
            status_distribution.append({
                'status': status_code,
                'count': count
            })
        
        # Time-based stats
        from datetime import datetime, timedelta
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        new_this_week = candidates.filter(created_at__date__gte=week_ago).count()
        new_this_month = candidates.filter(created_at__date__gte=month_ago).count()
        
        # Average experience
        avg_experience = candidates.aggregate(
            avg_exp=Avg('experience_years')
        )['avg_exp'] or 0
        
        # Top skills (assuming professional_skills is a JSONField with list)
        top_skills = []
        skills_count = {}
        for candidate in candidates.exclude(professional_skills__isnull=True):
            if candidate.professional_skills:
                for skill in candidate.professional_skills:
                    skills_count[skill] = skills_count.get(skill, 0) + 1
        
        # Sort and get top 10
        top_skills = [
            {'skill': skill, 'count': count}
            for skill, count in sorted(skills_count.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        # Top locations
        top_locations = list(
            candidates.exclude(location__isnull=True)
            .exclude(location='')
            .values('location')
            .annotate(count=Count('location'))
            .order_by('-count')[:10]
        )
        
        # Salary ranges (if you have salary_expectation field)
        salary_ranges = []
        if candidates.filter(salary_expectation__isnull=False).exists():
            ranges = [
                ('0-50k', 0, 50000),
                ('50k-75k', 50000, 75000),
                ('75k-100k', 75000, 100000),
                ('100k-150k', 100000, 150000),
                ('150k+', 150000, float('inf'))
            ]
            
            for range_label, min_sal, max_sal in ranges:
                if max_sal == float('inf'):
                    count = candidates.filter(salary_expectation__gte=min_sal).count()
                else:
                    count = candidates.filter(
                        salary_expectation__gte=min_sal,
                        salary_expectation__lt=max_sal
                    ).count()
                
                salary_ranges.append({
                    'range': range_label,
                    'count': count
                })
        
        return Response({
            'total_candidates': total_candidates,
            'by_status': status_distribution,
            'new_this_week': new_this_week,
            'new_this_month': new_this_month,
            'average_experience_years': round(avg_experience, 1),
            'top_skills': top_skills,
            'top_locations': top_locations,
            'salary_ranges': salary_ranges
        })
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update candidate hiring status"""
        candidate = self.get_object()
        new_status = request.data.get('status')
        reason = request.data.get('reason', '')
        
        if new_status not in dict(Candidate.HIRING_STATUS_CHOICES):
            return Response(
                {'error': 'Invalid status'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create status update record
        previous_status = candidate.hiring_status
        if previous_status != new_status:
            CandidateStatusUpdate.objects.create(
                candidate=candidate,
                previous_status=previous_status,
                new_status=new_status,
                reason=reason,
                updated_by=request.user
            )
            
            candidate.hiring_status = new_status
            candidate.save()
        
        return Response({'status': 'updated'})
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get candidate summary data"""
        candidate = self.get_object()
        
        summary = {
            'basic_info': {
                'name': candidate.name,
                'email': candidate.email,
                'phone': candidate.phone,
                'location': candidate.location
            },
            'professional_info': {
                'current_position': candidate.current_position,
                'current_company': candidate.current_company,
                'experience_years': candidate.experience_years,
                'skills_count': len(candidate.professional_skills or [])
            },
            'hiring_info': {
                'status': candidate.hiring_status,
                'overall_score': candidate.overall_score,
                'skill_match_percentage': candidate.skill_match_percentage
            },
            'activity_counts': {
                'work_experiences': candidate.work_experiences.count(),
                'education': candidate.education_history.count(),
                'projects': candidate.projects.count(),
                'attachments': candidate.attachments.count(),
                'emails': candidate.email_connections.count(),
                'applications': candidate.mpr_applications.count()
            }
        }
        
        return Response(summary)
    
    @action(detail=True, methods=['post'])
    def sync_emails(self, request, pk=None):
        """Sync emails for specific candidate"""
        candidate = self.get_object()
        
        result = EmailSyncService.sync_new_candidate_emails(candidate)
        
        return Response({
            'message': 'Email sync completed',
            'result': result
        })


class CandidateWorkExperienceViewSet(viewsets.ModelViewSet):
    """ViewSet for candidate work experience"""
    
    serializer_class = CandidateWorkExperienceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        candidate_pk = self.kwargs.get('candidate_pk')
        return CandidateWorkExperience.objects.filter(
            candidate_id=candidate_pk
        ).order_by('-start_date', 'display_order')
    
    def perform_create(self, serializer):
        candidate_pk = self.kwargs.get('candidate_pk')
        candidate = get_object_or_404(Candidate, pk=candidate_pk)
        serializer.save(candidate=candidate)


class CandidateEducationViewSet(viewsets.ModelViewSet):
    """ViewSet for candidate education"""
    
    serializer_class = CandidateEducationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        candidate_pk = self.kwargs.get('candidate_pk')
        return CandidateEducation.objects.filter(
            candidate_id=candidate_pk
        ).order_by('-start_date', 'display_order')
    
    def perform_create(self, serializer):
        candidate_pk = self.kwargs.get('candidate_pk')
        candidate = get_object_or_404(Candidate, pk=candidate_pk)
        serializer.save(candidate=candidate)


class CandidateProjectViewSet(viewsets.ModelViewSet):
    """ViewSet for candidate projects"""
    
    serializer_class = CandidateProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        candidate_pk = self.kwargs.get('candidate_pk')
        return CandidateProject.objects.filter(
            candidate_id=candidate_pk
        ).order_by('-is_featured', '-start_date', 'display_order')
    
    def perform_create(self, serializer):
        candidate_pk = self.kwargs.get('candidate_pk')
        candidate = get_object_or_404(Candidate, pk=candidate_pk)
        serializer.save(candidate=candidate)


class CandidateReferenceViewSet(viewsets.ModelViewSet):
    """ViewSet for candidate references"""
    
    serializer_class = CandidateReferenceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        candidate_pk = self.kwargs.get('candidate_pk')
        return CandidateReference.objects.filter(
            candidate_id=candidate_pk
        ).order_by('reference_name')
    
    def perform_create(self, serializer):
        candidate_pk = self.kwargs.get('candidate_pk')
        candidate = get_object_or_404(Candidate, pk=candidate_pk)
        serializer.save(candidate=candidate)


class CandidateEmailConnectionViewSet(viewsets.ModelViewSet):
    """ViewSet for candidate email connections"""
    
    serializer_class = CandidateEmailConnectionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        candidate_pk = self.kwargs.get('candidate_pk')
        return CandidateEmailConnection.objects.filter(
            candidate_id=candidate_pk
        ).select_related('email_message').order_by('-email_message__received_datetime')
    
    def perform_create(self, serializer):
        candidate_pk = self.kwargs.get('candidate_pk')
        candidate = get_object_or_404(Candidate, pk=candidate_pk)
        serializer.save(candidate=candidate)


class CandidateAttachmentViewSet(viewsets.ModelViewSet):
    """ViewSet for candidate attachments"""
    
    serializer_class = CandidateAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        candidate_pk = self.kwargs.get('candidate_pk')
        return CandidateAttachment.objects.filter(
            candidate_id=candidate_pk
        ).order_by('-is_primary_cv', '-created_at')
    
    def perform_create(self, serializer):
        candidate_pk = self.kwargs.get('candidate_pk')
        candidate = get_object_or_404(Candidate, pk=candidate_pk)
        serializer.save(
            candidate=candidate,
            uploaded_by=self.request.user
        )
    
    @action(detail=True, methods=['post'])
    def set_primary_cv(self, request, candidate_pk=None, pk=None):
        """Set attachment as primary CV"""
        attachment = self.get_object()
        
        # Remove primary flag from other CVs
        CandidateAttachment.objects.filter(
            candidate_id=candidate_pk,
            is_primary_cv=True
        ).update(is_primary_cv=False)
        
        # Set this one as primary
        attachment.is_primary_cv = True
        attachment.save()
        
        return Response({'status': 'primary_cv_set'})


class CandidateStatusUpdateViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for candidate status updates (read-only)"""
    
    serializer_class = CandidateStatusUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        candidate_pk = self.kwargs.get('candidate_pk')
        return CandidateStatusUpdate.objects.filter(
            candidate_id=candidate_pk
        ).select_related('updated_by').order_by('-updated_at')


class CandidateMPRViewSet(viewsets.ModelViewSet):
    """ViewSet for candidate MPR applications"""
    
    serializer_class = CandidateMPRSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = CandidateMPRFilter
    
    def get_queryset(self):
        candidate_pk = self.kwargs.get('candidate_pk')
        return CandidateMPR.objects.filter(
            candidate_id=candidate_pk
        ).select_related('mpr', 'primary_cv', 'updated_by').order_by('-applied_at')
    
    def perform_create(self, serializer):
        candidate_pk = self.kwargs.get('candidate_pk')
        candidate = get_object_or_404(Candidate, pk=candidate_pk)
        serializer.save(candidate=candidate)


# Additional utility views

class CandidateAttachmentsByTypeView(APIView):
    """Get candidate attachments grouped by type"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, candidate_pk):
        candidate = get_object_or_404(Candidate, pk=candidate_pk)
        
        attachments_by_type = {}
        for attachment in candidate.attachments.all():
            file_type = attachment.file_type
            if file_type not in attachments_by_type:
                attachments_by_type[file_type] = []
            
            attachments_by_type[file_type].append(
                CandidateAttachmentSerializer(attachment, context={'request': request}).data
            )
        
        return Response(attachments_by_type)


class EmailAttachmentsView(APIView):
    """Get attachments for a specific email"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, candidate_pk, email_pk):
        candidate = get_object_or_404(Candidate, pk=candidate_pk)
        email_connection = get_object_or_404(
            CandidateEmailConnection, 
            pk=email_pk, 
            candidate=candidate
        )
        
        attachments = email_connection.attachments.all()
        serializer = CandidateAttachmentSerializer(
            attachments, 
            many=True, 
            context={'request': request}
        )
        
        return Response(serializer.data)


class UpdateMPRApplicationStageView(APIView):
    """Update MPR application stage"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, candidate_pk, application_pk):
        application = get_object_or_404(
            CandidateMPR, 
            pk=application_pk, 
            candidate_id=candidate_pk
        )
        
        new_stage = request.data.get('stage')
        if new_stage not in dict(CandidateMPR._meta.get_field('application_stage').choices):
            return Response(
                {'error': 'Invalid stage'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        application.application_stage = new_stage
        application.updated_by = request.user
        application.save()
        
        return Response({'status': 'stage_updated'})


class SetPrimaryCVView(APIView):
    """Set primary CV for MPR application"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, candidate_pk, application_pk):
        application = get_object_or_404(
            CandidateMPR, 
            pk=application_pk, 
            candidate_id=candidate_pk
        )
        
        attachment_id = request.data.get('attachment_id')
        if attachment_id:
            attachment = get_object_or_404(
                CandidateAttachment, 
                pk=attachment_id, 
                candidate_id=candidate_pk
            )
            application.primary_cv = attachment
        else:
            application.primary_cv = None
        
        application.updated_by = request.user
        application.save()
        
        return Response({'status': 'primary_cv_set'})


class SyncCandidateEmailsView(APIView):
    """Sync emails for all candidates or specific candidate"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        candidate_email = request.data.get('candidate_email')
        days_back = request.data.get('days_back', 30)
        
        result = EmailSyncService.sync_candidate_emails(
            candidate_email=candidate_email,
            days_back=days_back
        )
        
        return Response({
            'message': 'Email sync completed',
            'result': result
        })


class BulkUpdateCandidateStatusView(APIView):
    """Bulk update candidate status"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        candidate_ids = request.data.get('candidate_ids', [])
        new_status = request.data.get('status')
        reason = request.data.get('reason', 'Bulk update')
        
        if not candidate_ids or not new_status:
            return Response(
                {'error': 'candidate_ids and status are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_status not in dict(Candidate.HIRING_STATUS_CHOICES):
            return Response(
                {'error': 'Invalid status'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        updated_count = 0
        
        with transaction.atomic():
            for candidate_id in candidate_ids:
                try:
                    candidate = Candidate.objects.get(pk=candidate_id)
                    previous_status = candidate.hiring_status
                    
                    if previous_status != new_status:
                        # Create status update record
                        CandidateStatusUpdate.objects.create(
                            candidate=candidate,
                            previous_status=previous_status,
                            new_status=new_status,
                            reason=reason,
                            updated_by=request.user
                        )
                        
                        # Update candidate status
                        candidate.hiring_status = new_status
                        candidate.save()
                        
                        updated_count += 1
                
                except Candidate.DoesNotExist:
                    continue
        
        return Response({
            'message': f'Updated {updated_count} candidates',
            'updated_count': updated_count
        })