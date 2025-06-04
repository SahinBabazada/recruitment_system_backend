# mpr/views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from permissions.permissions import HasPermission
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import csv
from django.http import HttpResponse

from .models import (
    Job, OrganizationalUnit, Location, EmploymentType, HiringReason,
    Employee, TechnicalSkill, Language, Competency, ContractDuration,
    MPR, MPRComment, MPRStatusHistory
)
from .serializers import (
    JobSerializer, OrganizationalUnitSerializer, LocationSerializer,
    EmploymentTypeSerializer, HiringReasonSerializer, EmployeeSerializer,
    TechnicalSkillSerializer, LanguageSerializer, CompetencySerializer,
    ContractDurationSerializer, MPRListSerializer, MPRDetailSerializer,
    MPRCreateSerializer, MPRCommentSerializer, MPRApprovalSerializer,
    MPRStatusHistorySerializer
)
from .filters import MPRFilter

User = get_user_model()

class JobViewSet(viewsets.ModelViewSet):
    """ViewSet for managing job titles"""
    queryset = Job.objects.filter(is_active=True)
    serializer_class = JobSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'created_at']
    ordering = ['title']

    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Dynamic permission based on action"""
        permission_map = {
            'list': 'mpr:view',
            'retrieve': 'mpr:view',
            'create': 'mpr:create',
            'update': 'mpr:edit',
            'partial_update': 'mpr:edit',
            'destroy': 'mpr:delete',
        }
        
        required_permission = permission_map.get(self.action, 'mpr:view')
        return [HasPermission(required_permission)]

    @action(detail=False, methods=['post'], permission_classes=[HasPermission('mpr:edit')])
    def create_if_not_exists(self, request):
        """Create a job if it doesn't exist"""
        title = request.data.get('title', '').strip()
        if not title:
            return Response(
                {'error': 'Title is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        job, created = Job.objects.get_or_create(
            title=title,
            defaults={
                'description': request.data.get('description', ''),
                'created_by': request.user
            }
        )
        
        serializer = self.get_serializer(job)
        return Response(
            {
                'job': serializer.data,
                'created': created
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


class OrganizationalUnitViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for organizational units (read-only)"""
    queryset = OrganizationalUnit.objects.filter(is_active=True)
    serializer_class = OrganizationalUnitSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'code']
    filterset_fields = ['type', 'parent']
    ordering = ['type', 'name']

    def get_permissions(self):
        """Dynamic permission based on action"""
        permission_map = {
            'list': 'mpr:view',
            'retrieve': 'mpr:view',
            'departments': 'mpr:view',
            'divisions': 'mpr:view',
            'units': 'mpr:view',
        }
        required_permission = permission_map.get(self.action, 'mpr:view')
        return [HasPermission(required_permission)]

    @action(detail=False, methods=['get'], permission_classes=[HasPermission('mpr:view')])
    def departments(self, request):
        """Get all departments"""
        departments = self.queryset.filter(type='department')
        serializer = self.get_serializer(departments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[HasPermission('mpr:view')])
    def divisions(self, request):
        """Get divisions by department"""
        department_id = request.query_params.get('department')
        queryset = self.queryset.filter(type='division')
        if department_id:
            queryset = queryset.filter(parent_id=department_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[HasPermission('mpr:view')])
    def units(self, request):
        """Get units by department or division"""
        parent_id = request.query_params.get('parent')
        queryset = self.queryset.filter(type='unit')
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class LocationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for locations (read-only)"""
    queryset = Location.objects.filter(is_active=True)
    serializer_class = LocationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'city', 'country']
    filterset_fields = ['location_type', 'country']
    ordering = ['name']

    def get_permissions(self):
        """Dynamic permission based on action"""
        return [HasPermission('mpr:view')]


class EmploymentTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for employment types (read-only)"""
    queryset = EmploymentType.objects.filter(is_active=True)
    serializer_class = EmploymentTypeSerializer
    permission_classes = [IsAuthenticated]
    ordering = ['name']

    def get_permissions(self):
        """Dynamic permission based on action"""
        return [HasPermission('mpr:view')]


class HiringReasonViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for hiring reasons (read-only)"""
    queryset = HiringReason.objects.filter(is_active=True)
    serializer_class = HiringReasonSerializer
    permission_classes = [IsAuthenticated]
    ordering = ['name']

    def get_permissions(self):
        """Dynamic permission based on action"""
        return [HasPermission('mpr:view')]


class EmployeeViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for employees (read-only)"""
    queryset = Employee.objects.filter(is_active=True).select_related(
        'department', 'position', 'location'
    )
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['employee_id', 'first_name', 'last_name', 'email']
    filterset_fields = ['department', 'position', 'location']
    ordering = ['last_name', 'first_name']

    def get_permissions(self):
        """Dynamic permission based on action"""
        return [HasPermission('mpr:view')]


class TechnicalSkillViewSet(viewsets.ModelViewSet):
    """ViewSet for technical skills"""
    queryset = TechnicalSkill.objects.filter(is_active=True)
    serializer_class = TechnicalSkillSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'category', 'description']
    filterset_fields = ['category']
    ordering = ['category', 'name']

    def get_permissions(self):
        """Dynamic permission based on action"""
        permission_map = {
            'list': 'mpr:view',
            'retrieve': 'mpr:view',
            'create': 'mpr:edit',
            'update': 'mpr:edit',
            'partial_update': 'mpr:edit',
            'destroy': 'mpr:edit',
            'create_if_not_exists': 'mpr:edit',
        }
        required_permission = permission_map.get(self.action, 'mpr:view')
        return [HasPermission(required_permission)]

    @action(detail=False, methods=['post'], permission_classes=[HasPermission('mpr:edit')])
    def create_if_not_exists(self, request):
        """Create a technical skill if it doesn't exist"""
        name = request.data.get('name', '').strip()
        if not name:
            return Response(
                {'error': 'Name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        skill, created = TechnicalSkill.objects.get_or_create(
            name=name,
            defaults={
                'category': request.data.get('category', ''),
                'description': request.data.get('description', ''),
                'created_by': request.user
            }
        )
        
        serializer = self.get_serializer(skill)
        return Response(
            {
                'skill': serializer.data,
                'created': created
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


class LanguageViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for languages (read-only)"""
    queryset = Language.objects.filter(is_active=True)
    serializer_class = LanguageSerializer
    permission_classes = [IsAuthenticated]
    ordering = ['name']

    def get_permissions(self):
        """Dynamic permission based on action"""
        return [HasPermission('mpr:view')]


class CompetencyViewSet(viewsets.ModelViewSet):
    """ViewSet for competencies"""
    queryset = Competency.objects.filter(is_active=True)
    serializer_class = CompetencySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'category', 'description']
    filterset_fields = ['category']
    ordering = ['category', 'name']

    def get_permissions(self):
        """Dynamic permission based on action"""
        permission_map = {
            'list': 'mpr:view',
            'retrieve': 'mpr:view',
            'create': 'mpr:edit',
            'update': 'mpr:edit',
            'partial_update': 'mpr:edit',
            'destroy': 'mpr:edit',
            'create_if_not_exists': 'mpr:edit',
        }
        required_permission = permission_map.get(self.action, 'mpr:view')
        return [HasPermission(required_permission)]

    @action(detail=False, methods=['post'], permission_classes=[HasPermission('mpr:edit')])
    def create_if_not_exists(self, request):
        """Create a competency if it doesn't exist"""
        name = request.data.get('name', '').strip()
        if not name:
            return Response(
                {'error': 'Name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        competency, created = Competency.objects.get_or_create(
            name=name,
            defaults={
                'category': request.data.get('category', ''),
                'description': request.data.get('description', ''),
                'created_by': request.user
            }
        )
        
        serializer = self.get_serializer(competency)
        return Response(
            {
                'competency': serializer.data,
                'created': created
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


class ContractDurationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for contract durations (read-only)"""
    queryset = ContractDuration.objects.filter(is_active=True)
    serializer_class = ContractDurationSerializer
    permission_classes = [IsAuthenticated]
    ordering = ['months']

    def get_permissions(self):
        """Dynamic permission based on action"""
        return [HasPermission('mpr:view')]


class MPRViewSet(viewsets.ModelViewSet):
    """ViewSet for MPR forms"""
    queryset = MPR.objects.select_related(
        'job_title', 'department', 'division', 'unit', 'location',
        'employment_type', 'hiring_reason', 'replaced_employee',
        'contract_duration', 'created_by', 'updated_by', 'approved_by',
        'rejected_by', 'recruiter', 'budget_holder'
    ).prefetch_related(
        'technical_skills', 'required_languages', 'core_competencies',
        'comments', 'status_history'
    )
    # Remove the problematic annotation - the property will handle this
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = MPRFilter
    search_fields = [
        'mpr_number', 'job_title__title', 'department__name',
        'business_justification', 'created_by__username'
    ]
    ordering_fields = [
        'mpr_number', 'created_at', 'desired_start_date', 'priority', 'status'
    ]
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        user = self.request.user
        queryset = super().get_queryset()
        
        if user.has_permission('mpr:view_all'):
            return queryset
        return queryset.filter(
            Q(created_by=user) |
            Q(recruiter=user) |
            Q(budget_holder=user)
        )

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return MPRListSerializer
        elif self.action == 'create':
            return MPRCreateSerializer
        else:
            return MPRDetailSerializer

    def get_permissions(self):
        """Dynamic permission based on action"""
        permission_map = {
            'list': 'mpr:view',
            'retrieve': 'mpr:view',
            'create': 'mpr:create',
            'update': 'mpr:edit',
            'partial_update': 'mpr:edit',
            'destroy': 'mpr:delete',
            'approve': 'mpr:approve',
            'submit_for_approval': 'mpr:edit',
            'add_comment': 'mpr:comment',
            'comments': 'mpr:view',
            'status_history': 'mpr:view',
            'dashboard_stats': [],
            'my_tasks': [],
            'export': 'mpr:export',
        }
        required_permission = permission_map.get(self.action, 'mpr:view')
        return [HasPermission(required_perm) for required_perm in required_permission] if isinstance(required_permission, list) else [HasPermission(required_permission)]

    def perform_update(self, serializer):
        """Check if user can edit this MPR"""
        instance = self.get_object()
        if not instance.can_edit(self.request.user):
            raise permissions.PermissionDenied("You cannot edit this MPR")
        serializer.save()

    def perform_destroy(self):
        instance = self.get_object()
        if not instance.can_edit(self.request.user):
            return Response(
                {'error': 'You cannot delete this MPR'},
                status=status.HTTP_403_FORBIDDEN
            )
        instance.delete()

    @action(detail=True, methods=['post'], permission_classes=[HasPermission('mpr:approve')])
    def approve(self, request, pk=None):
        """Moderate an MPR"""
        mpr = self.get_object()
        serializer = MPRApprovalSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        if not mpr.can_approve(request.user):
            return Response(
                {'error': 'You cannot approve this MPR'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        action = request.data.get('action')
        reason = request.data.get('reason', '')
        
        try:
            if action == 'approve':
                mpr.approve(request.user)
                message = 'MPR approved successfully'
            else:
                mpr.reject(request.user, reason=reason)
                message = 'MPR rejected successfully'
            
            MPRStatusHistory.objects.create(
                mpr=mpr,
                from_status='pending',
                to_status=mpr.status,
                changed_by=request.user,
                reason=reason
            )
            
            return Response({'message': message, 'status': mpr.status})
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], permission_classes=[HasPermission('mpr:edit')])
    def submit_for_approval(self, request, pk=None):
        """Submit MPR for approval"""
        mpr = self.get_object()
        
        if mpr.status != 'draft':
            return Response(
                {'error': 'Only draft MPRs can be submitted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not mpr.can_edit(request.user):
            return Response(
                {'error': 'You cannot submit this MPR'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        MPRStatusHistory.objects.create(
            mpr=mpr,
            from_status=mpr.status,
            to_status='pending',
            changed_by=request.user,
            reason='submitted for approval'
        )
        
        mpr.status = 'pending'
        mpr.save(update_fields=['status'])
        
        return Response({'status': 'MPR submitted for approval'})

    @action(detail=True, methods=['post'], permission_classes=[HasPermission('mpr:comment')])
    def add_comment(self, request, pk=None):
        """Add comment to MPR"""
        mpr = self.get_object()
        serializer = MPRCommentSerializer(data=request.data, context={'user': request.user, 'mpr': mpr})
        
        if serializer.is_valid():
            serializer.save(mpr=mpr, user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], permission_classes=[HasPermission('mpr:view')])
    def comments(self, request, pk=None):
        """Get MPR comments"""
        mpr = self.get_object()
        comments = mpr.comments.all()
        
        if not request.user.has_permission('mpr:view_internal_comments'):
            comments = comments.filter(is_internal=False)
        
        serializer = MPRCommentSerializer(comments, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], permission_classes=[HasPermission('mpr:view')])
    def status_history(self, request, pk=None):
        """Get MPR status history"""
        mpr = self.get_object()
        history = mpr.status_history.all()
        serializer = MPRStatusHistorySerializer(history, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[])
    def dashboard_stats(self, request):
        """Get dashboard statistics for MPRs"""
        queryset = self.get_queryset()
        
        stats = {
            'total': queryset.count(),
            'draft': queryset.filter(status='draft').count(),
            'pending': queryset.filter(status='pending').count(),
            'approved': queryset.filter(status='approved').count(),
            'rejected': queryset.filter(status='rejected').count(),
            'my_mprs': queryset.filter(created_by=request.user).count(),
            'pending_my_approval': queryset.filter(status='pending').count() if request.user.has_permission('mpr:approve') else 0,
            'high_priority': queryset.filter(priority='high').count(),
            'urgent_priority': queryset.filter(priority='urgent').count(),
            'recent_activity': queryset.filter(created_at__gte=timezone.now() - timedelta(days=7)).count(),
        }
        
        return Response(stats)

    @action(detail=False, methods=['get'], permission_classes=[])
    def my_tasks(self, request):
        """Get user's MPR-related tasks"""
        user = request.user
        tasks = {
            'drafts_to_complete': [],
            'pending_approval': [],
            'assigned_as_recruiter': [],
            'budget_holder_for': []
        }
        
        drafts = self.get_queryset().filter(created_by=user, status='draft')[:5]
        tasks['drafts_to_complete'] = MPRListSerializer(drafts, many=True).data
        
        if user.has_permission('mpr:approve'):
            pending = self.get_queryset().filter(status='pending')[:5]
            tasks['pending_approval'] = MPRListSerializer(pending, many=True).data
        
        recruiter_mprs = self.get_queryset().filter(recruiter=user, status__in=['approved'])[:5]
        tasks['assigned_as_recruiter'] = MPRListSerializer(recruiter_mprs, many=True).data
        
        budget_mprs = self.get_queryset().filter(budget_holder=user, status__in=['pending', 'approved'])[:5]
        tasks['budget_holder_for'] = MPRListSerializer(budget_mprs, many=True).data
        
        return Response(tasks)

    @action(detail=False, methods=['get'], permission_classes=[HasPermission('mpr:export')])
    def export(self, request):
        """Export MPRs to CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="mprs.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'MPR Number', 'Job Title', 'Department', 'Status', 'Priority',
            'Location', 'Desired Start Date', 'Created By', 'Created At'
        ])
        
        queryset = self.filter_queryset(self.get_queryset())
        for mpr in queryset:
            writer.writerow([
                mpr.mpr_number,
                mpr.job_title.title,
                mpr.department.name,
                mpr.get_status_display(),
                mpr.get_priority_display(),
                mpr.location.name,
                mpr.desired_start_date,
                mpr.created_by.username,
                mpr.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return response