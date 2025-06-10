# mpr/views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
from django.db import transaction
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
    MPR, MPRComment, MPRStatusHistory, Recruiter, Manager, BudgetHolder, BudgetSponsor
)
from .serializers import (
    JobSerializer, OrganizationalUnitSerializer, LocationSerializer,
    EmploymentTypeSerializer, HiringReasonSerializer, EmployeeSerializer,
    TechnicalSkillSerializer, LanguageSerializer, CompetencySerializer,
    ContractDurationSerializer, MPRListSerializer, MPRDetailSerializer,
    MPRCreateSerializer, MPRCommentSerializer, MPRApprovalSerializer,
    MPRStatusHistorySerializer,OrganizationalUnitListSerializer, OrganizationalUnitDetailSerializer,
    OrganizationalUnitCreateSerializer, RecruiterSerializer, ManagerSerializer,
    BudgetHolderSerializer, BudgetSponsorSerializer, RoleAssignmentBulkSerializer,
    UserSerializer
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

# class OrganizationalUnitViewSet(viewsets.ReadOnlyModelViewSet):
#     """ViewSet for organizational units (read-only)"""
#     queryset = OrganizationalUnit.objects.filter(is_active=True)
#     serializer_class = OrganizationalUnitSerializer
#     permission_classes = [IsAuthenticated]
#     filter_backends = [DjangoFilterBackend, filters.SearchFilter]
#     search_fields = ['name', 'code']
#     filterset_fields = ['type', 'parent']
#     ordering = ['type', 'name']

#     def get_permissions(self):
#         """Dynamic permission based on action"""
#         permission_map = {
#             'list': 'mpr:view',
#             'retrieve': 'mpr:view',
#             'departments': 'mpr:view',
#             'divisions': 'mpr:view',
#             'units': 'mpr:view',
#         }
#         required_permission = permission_map.get(self.action, 'mpr:view')
#         return [HasPermission(required_permission)]

#     @action(detail=False, methods=['get'], permission_classes=[HasPermission('mpr:view')])
#     def departments(self, request):
#         """Get all departments"""
#         departments = self.queryset.filter(type='department')
#         serializer = self.get_serializer(departments, many=True)
#         return Response(serializer.data)

#     @action(detail=False, methods=['get'], permission_classes=[HasPermission('mpr:view')])
#     def divisions(self, request):
#         """Get divisions by department"""
#         department_id = request.query_params.get('department')
#         queryset = self.queryset.filter(type='division')
#         if department_id:
#             queryset = queryset.filter(parent_id=department_id)
#         serializer = self.get_serializer(queryset, many=True)
#         return Response(serializer.data)

#     @action(detail=False, methods=['get'], permission_classes=[HasPermission('mpr:view')])
#     def units(self, request):
#         """Get units by department or division"""
#         parent_id = request.query_params.get('parent')
#         queryset = self.queryset.filter(type='unit')
#         if parent_id:
#             queryset = queryset.filter(parent_id=parent_id)
#         serializer = self.get_serializer(queryset, many=True)
#         return Response(serializer.data)

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

# mpr/views.py (Additional views for organizational management)



class OrganizationalUnitViewSet(viewsets.ModelViewSet):
    """Enhanced ViewSet for organizational unit management"""
    queryset = OrganizationalUnit.objects.select_related(
        'parent', 'location', 'created_by',
        'primary_recruiter', 'primary_manager', 
        'primary_budget_holder', 'primary_budget_sponsor'
    ).prefetch_related(
        'children', 'recruiters__user', 'managers__user',
        'budget_holders__user', 'budget_sponsors__user'
    )
    
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code', 'description']
    filterset_fields = ['type', 'parent', 'location', 'is_active']
    ordering_fields = ['name', 'type', 'created_at', 'current_headcount']
    ordering = ['type', 'name']

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return OrganizationalUnitListSerializer
        elif self.action == 'create':
            return OrganizationalUnitCreateSerializer
        else:
            return OrganizationalUnitDetailSerializer

    def get_permissions(self):
        """Dynamic permission based on action"""
        permission_map = {
            'list': 'mpr:view',
            'retrieve': 'mpr:view',
            'create': 'mpr:create',
            'update': 'mpr:edit',
            'partial_update': 'mpr:edit',
            'destroy': 'mpr:delete',
            'assign_role': 'mpr:edit',
            'remove_role': 'mpr:edit',
            'bulk_assign_roles': 'mpr:edit',
            'update_primary_roles': 'mpr:edit',
            'hierarchy': 'mpr:view',
            'stats': 'mpr:view',
            'headcount_report': 'mpr:view',
        }
        required_permission = permission_map.get(self.action, 'mpr:view')
        return [HasPermission(required_permission)]

    def get_queryset(self):
        """Filter queryset based on user permissions and query params"""
        queryset = super().get_queryset()
        
        # Filter by active status if not explicitly specified
        if 'is_active' not in self.request.query_params:
            queryset = queryset.filter(is_active=True)
        
        return queryset

    @action(detail=True, methods=['post'])
    def assign_role(self, request, pk=None):
        """Assign a user to a specific role in this organizational unit"""
        org_unit = self.get_object()
        role_type = request.data.get('role_type')
        user_id = request.data.get('user_id')
        is_primary = request.data.get('is_primary', False)
        
        if not role_type or not user_id:
            return Response(
                {'error': 'role_type and user_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        role_models = {
            'recruiter': Recruiter,
            'manager': Manager,
            'budget_holder': BudgetHolder,
            'budget_sponsor': BudgetSponsor,
        }
        
        if role_type not in role_models:
            return Response(
                {'error': 'Invalid role_type'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # If setting as primary, unset other primary roles of same type
                if is_primary:
                    role_models[role_type].objects.filter(
                        organizational_unit=org_unit,
                        is_primary=True
                    ).update(is_primary=False)
                
                # Create or update role assignment
                role_data = {
                    'user': user,
                    'organizational_unit': org_unit,
                    'is_primary': is_primary,
                    'assigned_by': request.user
                }
                
                # Add role-specific data
                if role_type == 'recruiter':
                    role_data['specialization'] = request.data.get('specialization', '')
                elif role_type == 'manager':
                    role_data['manager_type'] = request.data.get('manager_type', 'line_manager')
                elif role_type == 'budget_holder':
                    role_data['budget_limit'] = request.data.get('budget_limit')
                    role_data['budget_type'] = request.data.get('budget_type', 'operational')
                elif role_type == 'budget_sponsor':
                    role_data['approval_limit'] = request.data.get('approval_limit')
                    role_data['sponsor_level'] = request.data.get('sponsor_level', 'level_1')
                
                role_obj, created = role_models[role_type].objects.get_or_create(
                    user=user,
                    organizational_unit=org_unit,
                    defaults=role_data
                )
                
                if not created:
                    # Update existing role
                    for key, value in role_data.items():
                        if key not in ['user', 'organizational_unit']:
                            setattr(role_obj, key, value)
                    role_obj.save()
                
                # Update primary role in organizational unit if needed
                if is_primary:
                    primary_field = f'primary_{role_type}'
                    setattr(org_unit, primary_field, user)
                    org_unit.save(update_fields=[primary_field])
                
                return Response({
                    'message': f'User assigned as {role_type}',
                    'created': created
                }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
                
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def remove_role(self, request, pk=None):
        """Remove a user from a specific role in this organizational unit"""
        org_unit = self.get_object()
        role_type = request.data.get('role_type')
        user_id = request.data.get('user_id')
        
        if not role_type or not user_id:
            return Response(
                {'error': 'role_type and user_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        role_models = {
            'recruiter': Recruiter,
            'manager': Manager,
            'budget_holder': BudgetHolder,
            'budget_sponsor': BudgetSponsor,
        }
        
        if role_type not in role_models:
            return Response(
                {'error': 'Invalid role_type'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                role_obj = role_models[role_type].objects.get(
                    user_id=user_id,
                    organizational_unit=org_unit
                )
                
                # If this was a primary role, clear it from org unit
                if role_obj.is_primary:
                    primary_field = f'primary_{role_type}'
                    setattr(org_unit, primary_field, None)
                    org_unit.save(update_fields=[primary_field])
                
                role_obj.delete()
                
                return Response({'message': f'User removed from {role_type} role'})
                
        except role_models[role_type].DoesNotExist:
            return Response(
                {'error': 'Role assignment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def bulk_assign_roles(self, request):
        """Bulk assign roles to multiple users"""
        serializer = RoleAssignmentBulkSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        org_unit = OrganizationalUnit.objects.get(id=data['organizational_unit_id'])
        role_type = data['role_type']
        user_ids = data['user_ids']
        
        role_models = {
            'recruiter': Recruiter,
            'manager': Manager,
            'budget_holder': BudgetHolder,
            'budget_sponsor': BudgetSponsor,
        }
        
        try:
            with transaction.atomic():
                created_count = 0
                updated_count = 0
                
                for user_id in user_ids:
                    user = User.objects.get(id=user_id)
                    
                    role_data = {
                        'user': user,
                        'organizational_unit': org_unit,
                        'is_primary': data.get('is_primary', False),
                        'assigned_by': request.user
                    }
                    
                    # Add role-specific data
                    if role_type == 'recruiter' and data.get('specialization'):
                        role_data['specialization'] = data['specialization']
                    elif role_type == 'manager' and data.get('manager_type'):
                        role_data['manager_type'] = data['manager_type']
                    elif role_type == 'budget_holder':
                        if data.get('budget_limit'):
                            role_data['budget_limit'] = data['budget_limit']
                        if data.get('budget_type'):
                            role_data['budget_type'] = data['budget_type']
                    elif role_type == 'budget_sponsor':
                        if data.get('approval_limit'):
                            role_data['approval_limit'] = data['approval_limit']
                        if data.get('sponsor_level'):
                            role_data['sponsor_level'] = data['sponsor_level']
                    
                    role_obj, created = role_models[role_type].objects.get_or_create(
                        user=user,
                        organizational_unit=org_unit,
                        defaults=role_data
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        # Update existing role
                        for key, value in role_data.items():
                            if key not in ['user', 'organizational_unit']:
                                setattr(role_obj, key, value)
                        role_obj.save()
                        updated_count += 1
                
                return Response({
                    'message': f'Bulk assignment completed',
                    'created': created_count,
                    'updated': updated_count
                })
                
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['patch'])
    def update_primary_roles(self, request, pk=None):
        """Update primary role assignments for an organizational unit"""
        org_unit = self.get_object()
        
        primary_fields = {
            'primary_recruiter_id': 'primary_recruiter',
            'primary_manager_id': 'primary_manager',
            'primary_budget_holder_id': 'primary_budget_holder',
            'primary_budget_sponsor_id': 'primary_budget_sponsor',
        }
        
        updated_fields = []
        
        for field_id, field_name in primary_fields.items():
            if field_id in request.data:
                user_id = request.data[field_id]
                
                if user_id:
                    try:
                        user = User.objects.get(id=user_id)
                        setattr(org_unit, field_name, user)
                        updated_fields.append(field_name)
                    except User.DoesNotExist:
                        return Response(
                            {'error': f'User with id {user_id} not found'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                else:
                    setattr(org_unit, field_name, None)
                    updated_fields.append(field_name)
        
        if updated_fields:
            org_unit.save(update_fields=updated_fields)
        
        serializer = self.get_serializer(org_unit)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def hierarchy(self, request):
        """Get organizational hierarchy tree"""
        # Get root departments
        departments = self.get_queryset().filter(type='department', parent=None)
        
        def build_tree(units):
            result = []
            for unit in units:
                unit_data = OrganizationalUnitListSerializer(unit, context={'request': request}).data
                children = unit.children.filter(is_active=True).order_by('name')
                if children:
                    unit_data['children'] = build_tree(children)
                result.append(unit_data)
            return result
        
        tree = build_tree(departments)
        return Response(tree)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get organizational unit statistics"""
        queryset = self.get_queryset()
        
        stats = {
            'total_units': queryset.count(),
            'departments': queryset.filter(type='department').count(),
            'divisions': queryset.filter(type='division').count(),
            'units': queryset.filter(type='unit').count(),
            'total_headcount': sum(unit.current_headcount for unit in queryset),
            'units_over_capacity': queryset.filter(
                current_headcount__gt=models.F('headcount_limit'),
                headcount_limit__isnull=False
            ).count(),
            'units_with_all_roles_assigned': queryset.filter(
                primary_recruiter__isnull=False,
                primary_manager__isnull=False,
                primary_budget_holder__isnull=False,
                primary_budget_sponsor__isnull=False
            ).count(),
            'recent_updates': queryset.filter(
                updated_at__gte=timezone.now() - timedelta(days=7)
            ).count(),
        }
        
        # Calculate average headcount utilization
        units_with_limits = queryset.filter(headcount_limit__isnull=False, headcount_limit__gt=0)
        if units_with_limits:
            total_utilization = sum(
                (unit.current_headcount / unit.headcount_limit) * 100 
                for unit in units_with_limits
            )
            stats['average_headcount_utilization'] = total_utilization / units_with_limits.count()
        else:
            stats['average_headcount_utilization'] = 0
        
        return Response(stats)

    @action(detail=False, methods=['get'])
    def headcount_report(self, request):
        """Get detailed headcount report"""
        queryset = self.get_queryset().filter(headcount_limit__isnull=False)
        
        report = []
        for unit in queryset:
            utilization = (unit.current_headcount / unit.headcount_limit) * 100 if unit.headcount_limit else 0
            
            report.append({
                'id': unit.id,
                'name': unit.name,
                'type': unit.type,
                'full_path': unit.get_full_path(),
                'current_headcount': unit.current_headcount,
                'headcount_limit': unit.headcount_limit,
                'utilization_percentage': round(utilization, 2),
                'available_positions': max(0, unit.headcount_limit - unit.current_headcount),
                'over_capacity': unit.current_headcount > unit.headcount_limit,
                'primary_manager': unit.primary_manager.get_full_name() if unit.primary_manager else None,
            })
        
        # Sort by utilization percentage (highest first)
        report.sort(key=lambda x: x['utilization_percentage'], reverse=True)
        
        return Response({
            'report': report,
            'summary': {
                'total_units': len(report),
                'over_capacity_units': len([r for r in report if r['over_capacity']]),
                'high_utilization_units': len([r for r in report if r['utilization_percentage'] >= 90]),
                'total_headcount': sum(r['current_headcount'] for r in report),
                'total_capacity': sum(r['headcount_limit'] for r in report),
                'available_positions': sum(r['available_positions'] for r in report),
            }
        })

class RecruiterViewSet(viewsets.ModelViewSet):
    queryset = Recruiter.objects.select_related('user', 'organizational_unit', 'assigned_by')
    serializer_class = RecruiterSerializer
    permission_classes = [HasPermission('mpr:edit')]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['organizational_unit', 'is_primary', 'is_active']
    search_fields = ['user__first_name', 'user__last_name', 'specialization']

class ManagerViewSet(viewsets.ModelViewSet):
    queryset = Manager.objects.select_related('user', 'organizational_unit', 'assigned_by')
    serializer_class = ManagerSerializer
    permission_classes = [HasPermission('mpr:edit')]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['organizational_unit', 'is_primary', 'manager_type', 'is_active']
    search_fields = ['user__first_name', 'user__last_name']

class BudgetHolderViewSet(viewsets.ModelViewSet):
    queryset = BudgetHolder.objects.select_related('user', 'organizational_unit', 'assigned_by')
    serializer_class = BudgetHolderSerializer
    permission_classes = [HasPermission('mpr:edit')]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['organizational_unit', 'is_primary', 'budget_type', 'is_active']
    search_fields = ['user__first_name', 'user__last_name']

class BudgetSponsorViewSet(viewsets.ModelViewSet):
    queryset = BudgetSponsor.objects.select_related('user', 'organizational_unit', 'assigned_by')
    serializer_class = BudgetSponsorSerializer
    permission_classes = [HasPermission('mpr:edit')]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['organizational_unit', 'is_primary', 'sponsor_level', 'is_active']
    search_fields = ['user__first_name', 'user__last_name']