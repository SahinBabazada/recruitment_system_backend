# mpr/views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg, F, Sum, Case, When, IntegerField
from django.db import transaction
from django.shortcuts import get_object_or_404
from permissions.permissions import HasPermission
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
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
    MPRStatusHistorySerializer, OrganizationalUnitListSerializer, OrganizationalUnitDetailSerializer,
    OrganizationalUnitCreateSerializer, RecruiterSerializer, ManagerSerializer,
    BudgetHolderSerializer, BudgetSponsorSerializer, RoleAssignmentBulkSerializer, OrganizationalUnitStatsSerializer,
    UserSerializer
)

from .filters import MPRFilter

try:
    from flows.utils import execute_flow_for_mpr, FlowExecutor
    from flows.models import Flow
    FLOWS_AVAILABLE = True
except ImportError:
    FLOWS_AVAILABLE = False
    
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
    """Enhanced MPR ViewSet with Flow Integration"""
    queryset = MPR.objects.select_related(
        'job_title', 'department', 'division', 'unit', 'location',
        'employment_type', 'hiring_reason', 'replaced_employee',
        'contract_duration', 'created_by', 'updated_by', 'approved_by',
        'rejected_by', 'recruiter', 'budget_holder'
    ).prefetch_related(
        'technical_skills', 'required_languages', 'core_competencies',
        'comments', 'status_history'
    )
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
            'preview_approval_flow': 'mpr:view',
            'get_approver_options': 'mpr:view',
        }
        required_permission = permission_map.get(self.action, 'mpr:view')
        return [HasPermission(required_perm) for required_perm in required_permission] if isinstance(required_permission, list) else [HasPermission(required_permission)]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Enhanced create with flow integration"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create the MPR
        mpr = serializer.save()
        
        # If MPR is being submitted for approval, start flow execution
        if mpr.status == 'pending' and FLOWS_AVAILABLE:
            try:
                active_flow = Flow.get_active_flow()
                if active_flow:
                    # Execute flow for this MPR
                    flow_execution = execute_flow_for_mpr(mpr)
                    
                    # Add flow execution info to response
                    response_data = serializer.data
                    response_data['flow_execution'] = {
                        'id': flow_execution.id,
                        'flow_name': active_flow.name,
                        'flow_version': active_flow.version,
                        'status': flow_execution.status,
                        'current_step': flow_execution.current_node.name if flow_execution.current_node else None
                    }
                    
                    return Response(response_data, status=status.HTTP_201_CREATED)
            except Exception as e:
                # Log error but don't fail MPR creation
                print(f"Flow execution failed for MPR {mpr.mpr_number}: {str(e)}")
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

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

    @action(detail=False, methods=['post'], permission_classes=[HasPermission('mpr:view')])
    def preview_approval_flow(self, request):
        """Preview approval flow for given MPR parameters"""
        if not FLOWS_AVAILABLE:
            return Response({
                'error': 'Flow system not available',
                'approval_steps': []
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get form data from request
            department_id = request.data.get('department_id')
            priority = request.data.get('priority', 'medium')
            employment_type_id = request.data.get('employment_type_id')
            hiring_reason_id = request.data.get('hiring_reason_id')
            location_id = request.data.get('location_id')
            budget_amount = request.data.get('budget_amount', 50000)  # Default
            
            # Get active flow
            active_flow = Flow.get_active_flow()
            if not active_flow:
                return Response({
                    'error': 'No active flow found',
                    'approval_steps': []
                })
            
            # Build execution context
            execution_context = self._build_preview_context(
                department_id, priority, employment_type_id, 
                hiring_reason_id, location_id, budget_amount
            )
            
            # Simulate flow execution
            approval_steps = self._simulate_flow_execution(active_flow, execution_context)
            
            # Get approver options for each step
            for step in approval_steps:
                if step['type'] == 'approval' and step.get('approver_type'):
                    step['approver_options'] = self._get_approver_options(
                        step['approver_type'], department_id
                    )
            
            return Response({
                'flow': {
                    'id': active_flow.id,
                    'name': active_flow.name,
                    'version': active_flow.version
                },
                'approval_steps': approval_steps,
                'execution_context': execution_context
            })
            
        except Exception as e:
            return Response({
                'error': f'Flow preview failed: {str(e)}',
                'approval_steps': []
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], permission_classes=[HasPermission('mpr:view')])
    def get_approver_options(self, request):
        """Get available approvers for a specific type and department"""
        approver_type = request.query_params.get('approver_type')
        department_id = request.query_params.get('department_id')
        
        if not approver_type or not department_id:
            return Response({
                'error': 'approver_type and department_id are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            department_id = int(department_id)
            approvers = self._get_approver_options(approver_type, department_id)
            return Response({
                'approver_type': approver_type,
                'department_id': department_id,
                'options': approvers
            })
        except Exception as e:
            return Response({
                'error': f'Failed to get approver options: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[HasPermission('mpr:approve')])
    def approve(self, request, pk=None):
        """Enhanced approve with flow integration"""
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
                
                # If flows are available, advance flow execution
                if FLOWS_AVAILABLE:
                    try:
                        flow_executions = mpr.flow_executions.filter(status='in_progress')
                        for execution in flow_executions:
                            # Find current approval step
                            current_step = execution.steps.filter(
                                status='in_progress',
                                assigned_to=request.user
                            ).first()
                            
                            if current_step:
                                executor = FlowExecutor(execution.flow, mpr)
                                executor.execution = execution
                                executor.approve_step(
                                    current_step.id, 
                                    request.user, 
                                    approved=True, 
                                    comments=reason
                                )
                    except Exception as e:
                        print(f"Flow advancement failed: {str(e)}")
                
                message = 'MPR approved successfully'
            else:
                mpr.reject(request.user, reason=reason)
                
                # If flows are available, mark flow as failed
                if FLOWS_AVAILABLE:
                    try:
                        flow_executions = mpr.flow_executions.filter(status='in_progress')
                        for execution in flow_executions:
                            execution.status = 'failed'
                            execution.error_message = f'Rejected by {request.user.username}: {reason}'
                            execution.completed_at = timezone.now()
                            execution.save()
                    except Exception as e:
                        print(f"Flow rejection failed: {str(e)}")
                
                message = 'MPR rejected successfully'
            
            MPRStatusHistory.objects.create(
                mpr=mpr,
                from_status='pending',
                to_status=mpr.status,
                changed_by=request.user,
                reason=reason
            )
            
            response_data = {'message': message, 'status': mpr.status}
            
            # Add flow information if available
            if FLOWS_AVAILABLE:
                flow_execution = mpr.flow_executions.filter(
                    status__in=['in_progress', 'completed', 'failed']
                ).first()
                if flow_execution:
                    response_data['flow_execution'] = {
                        'id': flow_execution.id,
                        'status': flow_execution.status,
                        'current_step': flow_execution.current_node.name if flow_execution.current_node else None,
                        'completed_at': flow_execution.completed_at
                    }
            
            return Response(response_data)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], permission_classes=[HasPermission('mpr:edit')])
    def submit_for_approval(self, request, pk=None):
        """Enhanced submit for approval with flow integration"""
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
        
        try:
            with transaction.atomic():
                # Update MPR status
                MPRStatusHistory.objects.create(
                    mpr=mpr,
                    from_status=mpr.status,
                    to_status='pending',
                    changed_by=request.user,
                    reason='submitted for approval'
                )
                
                mpr.status = 'pending'
                mpr.save(update_fields=['status'])
                
                response_data = {'status': 'MPR submitted for approval'}
                
                # Start flow execution if flows are available
                if FLOWS_AVAILABLE:
                    try:
                        active_flow = Flow.get_active_flow()
                        if active_flow:
                            flow_execution = execute_flow_for_mpr(mpr)
                            response_data['flow_execution'] = {
                                'id': flow_execution.id,
                                'flow_name': active_flow.name,
                                'flow_version': active_flow.version,
                                'status': flow_execution.status,
                                'current_step': flow_execution.current_node.name if flow_execution.current_node else None
                            }
                        else:
                            response_data['warning'] = 'No active flow found. Manual approval required.'
                    except Exception as e:
                        response_data['warning'] = f'Flow execution failed: {str(e)}. Manual approval required.'
                
                return Response(response_data)
                
        except Exception as e:
            return Response(
                {'error': f'Failed to submit MPR: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _build_preview_context(self, department_id, priority, employment_type_id, 
                              hiring_reason_id, location_id, budget_amount):
        """Build execution context for flow preview"""
        context = {
            'mpr_id': 'preview',
            'priority': priority,
            'budget_amount': float(budget_amount),
            'department': '',
            'employment_type': '',
            'location': '',
            'hiring_reason': '',
            'position_title': '',
        }
        
        try:
            if department_id:
                dept = OrganizationalUnit.objects.get(id=department_id)
                context['department'] = dept.name
                
            if employment_type_id:
                emp_type = EmploymentType.objects.get(id=employment_type_id)
                context['employment_type'] = emp_type.name
                
            if location_id:
                location = Location.objects.get(id=location_id)
                context['location'] = location.name
                
            if hiring_reason_id:
                reason = HiringReason.objects.get(id=hiring_reason_id)
                context['hiring_reason'] = reason.name
                
        except Exception as e:
            print(f"Error building context: {str(e)}")
        
        return context

    def _simulate_flow_execution(self, flow, context):
        """Simulate flow execution to determine approval path"""
        approval_steps = []
        
        # Get flow nodes and connections
        start_node = None
        nodes_dict = {}
        connections_dict = {}
        
        for node in flow.nodes.all():
            nodes_dict[node.node_id] = node
            if node.node_type == 'start':
                start_node = node
        
        for connection in flow.connections.all():
            if connection.start_node.node_id not in connections_dict:
                connections_dict[connection.start_node.node_id] = []
            connections_dict[connection.start_node.node_id].append(connection)
        
        if not start_node:
            return approval_steps
        
        # Traverse flow
        current_node_id = start_node.node_id
        step_order = 1
        visited_nodes = set()
        
        while current_node_id and current_node_id not in visited_nodes:
            visited_nodes.add(current_node_id)
            current_node = nodes_dict.get(current_node_id)
            
            if not current_node:
                break
            
            if current_node.node_type == 'approval':
                approval_steps.append({
                    'id': current_node.node_id,
                    'name': current_node.properties.get('name', f"{current_node.properties.get('approverType', 'Unknown')} Approval"),
                    'type': 'approval',
                    'approver_type': current_node.properties.get('approverType'),
                    'timeout_days': current_node.properties.get('timeoutDays', 5),
                    'order': step_order,
                    'status': 'will_execute'
                })
                step_order += 1
                
            elif current_node.node_type == 'condition':
                # Evaluate conditions
                condition_result = self._evaluate_node_conditions(current_node, context)
                
                # Find next connection based on condition result
                connections = connections_dict.get(current_node_id, [])
                next_connection = None
                
                for conn in connections:
                    if conn.connection_type == ('true' if condition_result else 'false'):
                        next_connection = conn
                        break
                
                if next_connection:
                    current_node_id = next_connection.end_node.node_id
                    continue
                else:
                    break
                    
            elif current_node.node_type == 'notification':
                approval_steps.append({
                    'id': current_node.node_id,
                    'name': current_node.properties.get('name', 'Notification'),
                    'type': 'notification',
                    'order': step_order,
                    'status': 'will_execute'
                })
                step_order += 1
                
            elif current_node.node_type == 'end':
                approval_steps.append({
                    'id': current_node.node_id,
                    'name': 'Flow Complete',
                    'type': 'end',
                    'order': step_order,
                    'status': 'will_execute'
                })
                break
            
            # Find next node
            connections = connections_dict.get(current_node_id, [])
            next_connection = None
            
            for conn in connections:
                if conn.connection_type == 'output':
                    next_connection = conn
                    break
            
            if next_connection:
                current_node_id = next_connection.end_node.node_id
            else:
                break
        
        return approval_steps

    def _evaluate_node_conditions(self, node, context):
        """Evaluate conditions for a condition node"""
        if not hasattr(node, 'conditions') or not node.conditions.exists():
            return True
        
        conditions = node.conditions.all()
        logic_operator = node.properties.get('logicOperator', 'AND')
        
        results = []
        for condition in conditions:
            field_value = context.get(condition.field, '')
            condition_value = condition.value
            
            result = False
            try:
                if condition.operator == 'equals':
                    result = str(field_value).lower() == str(condition_value).lower()
                elif condition.operator == 'not_equals':
                    result = str(field_value).lower() != str(condition_value).lower()
                elif condition.operator == 'greater_than':
                    result = float(field_value) > float(condition_value)
                elif condition.operator == 'less_than':
                    result = float(field_value) < float(condition_value)
                elif condition.operator == 'greater_equal':
                    result = float(field_value) >= float(condition_value)
                elif condition.operator == 'less_equal':
                    result = float(field_value) <= float(condition_value)
                elif condition.operator == 'contains':
                    result = str(condition_value).lower() in str(field_value).lower()
                elif condition.operator == 'starts_with':
                    result = str(field_value).lower().startswith(str(condition_value).lower())
                elif condition.operator == 'ends_with':
                    result = str(field_value).lower().endswith(str(condition_value).lower())
                elif condition.operator == 'in_list':
                    values = [v.strip().lower() for v in condition_value.split(',')]
                    result = str(field_value).lower() in values
                elif condition.operator == 'is_null':
                    result = not field_value or field_value == ''
                elif condition.operator == 'is_not_null':
                    result = field_value and field_value != ''
            except (ValueError, TypeError):
                result = False
            
            results.append(result)
        
        if logic_operator == 'AND':
            return all(results)
        else:  # OR
            return any(results)

    def _get_approver_options(self, approver_type, department_id):
        """Get available approvers based on type and department"""
        try:
            department = OrganizationalUnit.objects.get(id=department_id)
            
            if approver_type == 'manager':
                # Get managers for this department
                managers = Manager.objects.filter(
                    organizational_unit=department,
                    is_active=True
                ).select_related('user')
                
                return [{
                    'id': manager.user.id,
                    'full_name': manager.user.get_full_name() or manager.user.username,
                    'email': manager.user.email,
                    'position': getattr(manager.user, 'position', 'Manager'),
                    'is_primary': manager.is_primary,
                    'manager_type': manager.manager_type
                } for manager in managers]
                
            elif approver_type == 'budget_holder':
                # Get budget holders for this department
                budget_holders = BudgetHolder.objects.filter(
                    organizational_unit=department,
                    is_active=True
                ).select_related('user')
                
                return [{
                    'id': bh.user.id,
                    'full_name': bh.user.get_full_name() or bh.user.username,
                    'email': bh.user.email,
                    'position': getattr(bh.user, 'position', 'Budget Holder'),
                    'is_primary': bh.is_primary,
                    'budget_type': bh.budget_type,
                    'budget_limit': float(bh.budget_limit) if bh.budget_limit else None
                } for bh in budget_holders]
                
            elif approver_type == 'budget_sponsor':
                # Get budget sponsors for this department
                budget_sponsors = BudgetSponsor.objects.filter(
                    organizational_unit=department,
                    is_active=True
                ).select_related('user')
                
                return [{
                    'id': bs.user.id,
                    'full_name': bs.user.get_full_name() or bs.user.username,
                    'email': bs.user.email,
                    'position': getattr(bs.user, 'position', 'Budget Sponsor'),
                    'is_primary': bs.is_primary,
                    'sponsor_level': bs.sponsor_level,
                    'approval_limit': float(bs.approval_limit) if bs.approval_limit else None
                } for bs in budget_sponsors]
                
            elif approver_type == 'recruiter':
                # Get recruiters for this department
                recruiters = Recruiter.objects.filter(
                    organizational_unit=department,
                    is_active=True
                ).select_related('user')
                
                return [{
                    'id': recruiter.user.id,
                    'full_name': recruiter.user.get_full_name() or recruiter.user.username,
                    'email': recruiter.user.email,
                    'position': getattr(recruiter.user, 'position', 'Recruiter'),
                    'is_primary': recruiter.is_primary,
                    'specialization': recruiter.specialization
                } for recruiter in recruiters]
            
            else:
                # Fallback to employees in the department
                employees = Employee.objects.filter(
                    department=department,
                    is_active=True
                ).select_related('user', 'position')
                
                return [{
                    'id': emp.user.id if emp.user else emp.id,
                    'full_name': emp.full_name,
                    'email': emp.email,
                    'position': emp.position.title if emp.position else 'Employee',
                    'employee_id': emp.employee_id
                } for emp in employees if emp.user or emp.email]
                
        except OrganizationalUnit.DoesNotExist:
            return []
        except Exception as e:
            print(f"Error getting approver options: {str(e)}")
            return []

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

    @action(detail=True, methods=['get'], permission_classes=[HasPermission('mpr:view')])
    def flow_execution_status(self, request, pk=None):
        """Get flow execution status for this MPR"""
        mpr = self.get_object()
        
        if not FLOWS_AVAILABLE:
            return Response({
                'error': 'Flow system not available',
                'has_flow': False
            })
        
        try:
            # Get flow executions for this MPR
            flow_executions = mpr.flow_executions.all().order_by('-started_at')
            
            if not flow_executions.exists():
                return Response({
                    'has_flow': False,
                    'message': 'No flow execution found for this MPR'
                })
            
            # Get the latest execution
            latest_execution = flow_executions.first()
            
            # Get execution steps
            steps = latest_execution.steps.all().order_by('step_order')
            
            steps_data = []
            for step in steps:
                step_data = {
                    'id': step.id,
                    'step_order': step.step_order,
                    'node_name': step.node.name,
                    'node_type': step.node.node_type,
                    'status': step.status,
                    'started_at': step.started_at,
                    'completed_at': step.completed_at,
                    'assigned_to': {
                        'id': step.assigned_to.id,
                        'full_name': step.assigned_to.get_full_name(),
                        'email': step.assigned_to.email
                    } if step.assigned_to else None,
                    'approved_by': {
                        'id': step.approved_by.id,
                        'full_name': step.approved_by.get_full_name(),
                        'email': step.approved_by.email
                    } if step.approved_by else None,
                    'approved_at': step.approved_at,
                    'error_message': step.error_message,
                    'input_data': step.input_data,
                    'output_data': step.output_data
                }
                steps_data.append(step_data)
            
            execution_data = {
                'has_flow': True,
                'execution': {
                    'id': latest_execution.id,
                    'flow_name': latest_execution.flow.name,
                    'flow_version': latest_execution.flow.version,
                    'status': latest_execution.status,
                    'started_at': latest_execution.started_at,
                    'completed_at': latest_execution.completed_at,
                    'current_node': {
                        'id': latest_execution.current_node.id,
                        'name': latest_execution.current_node.name,
                        'type': latest_execution.current_node.node_type
                    } if latest_execution.current_node else None,
                    'error_message': latest_execution.error_message,
                    'execution_context': latest_execution.execution_context
                },
                'steps': steps_data,
                'pending_approvals': [
                    step_data for step_data in steps_data 
                    if step_data['status'] == 'in_progress' and step_data['assigned_to']
                ]
            }
            
            return Response(execution_data)
            
        except Exception as e:
            return Response({
                'error': f'Failed to get flow execution status: {str(e)}',
                'has_flow': False
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        
        # Add flow statistics if available
        if FLOWS_AVAILABLE:
            try:
                from flows.models import FlowExecution
                
                # Get flow execution statistics
                total_executions = FlowExecution.objects.count()
                active_executions = FlowExecution.objects.filter(status='in_progress').count()
                completed_executions = FlowExecution.objects.filter(status='completed').count()
                
                stats['flow_stats'] = {
                    'total_executions': total_executions,
                    'active_executions': active_executions,
                    'completed_executions': completed_executions,
                    'success_rate': (completed_executions / total_executions * 100) if total_executions > 0 else 0
                }
            except Exception as e:
                stats['flow_stats'] = {'error': str(e)}
        
        return Response(stats)

    @action(detail=False, methods=['get'], permission_classes=[])
    def my_tasks(self, request):
        """Get user's MPR-related tasks including flow approvals"""
        user = request.user
        tasks = {
            'drafts_to_complete': [],
            'pending_approval': [],
            'assigned_as_recruiter': [],
            'budget_holder_for': [],
            'flow_approvals': []
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
        
        # Add flow approval tasks if available
        if FLOWS_AVAILABLE:
            try:
                from flows.utils import get_pending_approvals_for_user
                
                pending_steps = get_pending_approvals_for_user(user)
                flow_approvals = []
                
                for step in pending_steps:
                    mpr = step.execution.mpr
                    flow_approvals.append({
                        'step_id': step.id,
                        'mpr': {
                            'id': mpr.id,
                            'mpr_number': mpr.mpr_number,
                            'job_title': mpr.job_title.title,
                            'department': mpr.department.name,
                            'created_at': mpr.created_at,
                            'priority': mpr.priority
                        },
                        'flow': {
                            'name': step.execution.flow.name,
                            'version': step.execution.flow.version
                        },
                        'step': {
                            'name': step.node.name,
                            'type': step.node.node_type,
                            'started_at': step.started_at,
                            'step_order': step.step_order
                        }
                    })
                
                tasks['flow_approvals'] = flow_approvals[:10]  # Limit to 10
                
            except Exception as e:
                tasks['flow_approvals'] = []
                print(f"Error getting flow approvals: {str(e)}")
        
        return Response(tasks)

    @action(detail=False, methods=['get'], permission_classes=[HasPermission('mpr:export')])
    def export(self, request):
        """Export MPRs to CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="mprs.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'MPR Number', 'Job Title', 'Department', 'Status', 'Priority',
            'Location', 'Desired Start Date', 'Created By', 'Created At',
            'Flow Status', 'Current Step'
        ])
        
        queryset = self.filter_queryset(self.get_queryset())
        for mpr in queryset:
            flow_status = 'No Flow'
            current_step = 'N/A'
            
            if FLOWS_AVAILABLE:
                try:
                    latest_execution = mpr.flow_executions.order_by('-started_at').first()
                    if latest_execution:
                        flow_status = latest_execution.status
                        if latest_execution.current_node:
                            current_step = latest_execution.current_node.name
                except Exception:
                    pass
            
            writer.writerow([
                mpr.mpr_number,
                mpr.job_title.title,
                mpr.department.name,
                mpr.get_status_display(),
                mpr.get_priority_display(),
                mpr.location.name,
                mpr.desired_start_date,
                mpr.created_by.username,
                mpr.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                flow_status,
                current_step
            ])
        
        return response
    
class OrganizationalUnitViewSet(viewsets.ModelViewSet):
    """Enhanced ViewSet for OrganizationalUnit with comprehensive functionality"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = OrganizationalUnit.objects.select_related(
            'parent', 'location', 'primary_recruiter', 'primary_manager',
            'primary_budget_holder', 'primary_budget_sponsor'
        ).prefetch_related(
            'children', 'recruiters', 'managers', 'budget_holders', 'budget_sponsors'
        ).annotate(
            children_count=Count('children', filter=Q(children__is_active=True)),
            total_roles_count=(
                Count('recruiters', filter=Q(recruiters__is_active=True)) +
                Count('managers', filter=Q(managers__is_active=True)) +
                Count('budget_holders', filter=Q(budget_holders__is_active=True)) +
                Count('budget_sponsors', filter=Q(budget_sponsors__is_active=True))
            ),
            active_recruiters_count=Count('recruiters', filter=Q(recruiters__is_active=True)),
            active_managers_count=Count('managers', filter=Q(managers__is_active=True)),
            active_budget_holders_count=Count('budget_holders', filter=Q(budget_holders__is_active=True)),
            active_budget_sponsors_count=Count('budget_sponsors', filter=Q(budget_sponsors__is_active=True))
        )
        
        # Apply filters
        unit_type = self.request.query_params.get('type')
        if unit_type:
            queryset = queryset.filter(type=unit_type)
            
        parent = self.request.query_params.get('parent')
        if parent:
            queryset = queryset.filter(parent_id=parent)
            
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(description__icontains=search)
            )
            
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
            
        location = self.request.query_params.get('location')
        if location:
            queryset = queryset.filter(location_id=location)
            
        cost_center = self.request.query_params.get('cost_center')
        if cost_center:
            queryset = queryset.filter(cost_center=cost_center)
        
        # Ordering
        ordering = self.request.query_params.get('ordering', 'name')
        queryset = queryset.order_by(ordering)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return OrganizationalUnitListSerializer
        elif self.action == 'create':
            return OrganizationalUnitCreateSerializer
        elif self.action == 'retrieve':
            return OrganizationalUnitDetailSerializer
        return OrganizationalUnitSerializer
    
    def retrieve(self, request, *args, **kwargs):
        """Enhanced retrieve with additional context"""
        instance = self.get_object()
        
        # Check if we should include additional data
        include_children = request.query_params.get('include_children', 'false').lower() == 'true'
        include_role_details = request.query_params.get('include_role_details', 'false').lower() == 'true'
        include_stats = request.query_params.get('include_stats', 'false').lower() == 'true'
        
        serializer = self.get_serializer(instance)
        data = serializer.data
        
        if include_children and instance.children.exists():
            children_serializer = OrganizationalUnitListSerializer(
                instance.children.filter(is_active=True), 
                many=True, 
                context=self.get_serializer_context()
            )
            data['children'] = children_serializer.data
            
        if include_role_details:
            # Add detailed role information
            data['role_details'] = {
                'recruiters': RecruiterSerializer(
                    instance.recruiters.filter(is_active=True), many=True
                ).data,
                'managers': ManagerSerializer(
                    instance.managers.filter(is_active=True), many=True
                ).data,
                'budget_holders': BudgetHolderSerializer(
                    instance.budget_holders.filter(is_active=True), many=True
                ).data,
                'budget_sponsors': BudgetSponsorSerializer(
                    instance.budget_sponsors.filter(is_active=True), many=True
                ).data,
            }
            
        if include_stats:
            # Add performance metrics
            data['performance_metrics'] = self._calculate_unit_performance(instance)
        
        return Response(data)

    @action(detail=True, methods=['get'])
    def role_assignments(self, request, pk=None):
        """Get detailed role assignments for a specific unit"""
        unit = self.get_object()
        
        # Get all role assignments with user details
        recruiters = Recruiter.objects.filter(
            organizational_unit=unit, is_active=True
        ).select_related('user', 'assigned_by').order_by('-is_primary', 'user__first_name')
        
        managers = Manager.objects.filter(
            organizational_unit=unit, is_active=True
        ).select_related('user', 'assigned_by').order_by('-is_primary', 'user__first_name')
        
        budget_holders = BudgetHolder.objects.filter(
            organizational_unit=unit, is_active=True
        ).select_related('user', 'assigned_by').order_by('-is_primary', 'user__first_name')
        
        budget_sponsors = BudgetSponsor.objects.filter(
            organizational_unit=unit, is_active=True
        ).select_related('user', 'assigned_by').order_by('-is_primary', 'user__first_name')
        
        # Calculate summary
        total_assignments = recruiters.count() + managers.count() + budget_holders.count() + budget_sponsors.count()
        primary_roles_filled = sum([
            bool(unit.primary_recruiter),
            bool(unit.primary_manager),
            bool(unit.primary_budget_holder),
            bool(unit.primary_budget_sponsor)
        ])
        
        missing_primary_roles = []
        if not unit.primary_recruiter:
            missing_primary_roles.append('Primary Recruiter')
        if not unit.primary_manager:
            missing_primary_roles.append('Primary Manager')
        if not unit.primary_budget_holder:
            missing_primary_roles.append('Primary Budget Holder')
        if not unit.primary_budget_sponsor:
            missing_primary_roles.append('Primary Budget Sponsor')
        
        response_data = {
            'recruiters': self._serialize_role_assignments(recruiters, 'recruiter'),
            'managers': self._serialize_role_assignments(managers, 'manager'),
            'budget_holders': self._serialize_role_assignments(budget_holders, 'budget_holder'),
            'budget_sponsors': self._serialize_role_assignments(budget_sponsors, 'budget_sponsor'),
            'summary': {
                'total_assignments': total_assignments,
                'active_assignments': total_assignments,  # Since we filter by is_active=True
                'primary_roles_filled': primary_roles_filled,
                'missing_primary_roles': missing_primary_roles
            }
        }
        
        return Response(response_data)

    @action(detail=True, methods=['post'])
    def assign_role(self, request, pk=None):
        """Assign a role to a user in this organizational unit"""
        unit = self.get_object()
        data = request.data.copy()
        data['organizational_unit'] = unit.id
        
        role_type = data.get('role_type')
        user_id = data.get('user_id')
        
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
        
        # Create the appropriate role assignment
        if role_type == 'recruiter':
            role, created = Recruiter.objects.get_or_create(
                user=user,
                organizational_unit=unit,
                defaults={
                    'is_primary': data.get('is_primary', False),
                    'specialization': data.get('specialization', ''),
                    'assigned_by': request.user
                }
            )
            serializer = RecruiterSerializer(role)
        elif role_type == 'manager':
            role, created = Manager.objects.get_or_create(
                user=user,
                organizational_unit=unit,
                defaults={
                    'is_primary': data.get('is_primary', False),
                    'manager_type': data.get('manager_type', 'line_manager'),
                    'assigned_by': request.user
                }
            )
            serializer = ManagerSerializer(role)
        elif role_type == 'budget_holder':
            role, created = BudgetHolder.objects.get_or_create(
                user=user,
                organizational_unit=unit,
                defaults={
                    'is_primary': data.get('is_primary', False),
                    'budget_limit': data.get('budget_limit'),
                    'budget_type': data.get('budget_type', 'operational'),
                    'assigned_by': request.user
                }
            )
            serializer = BudgetHolderSerializer(role)
        elif role_type == 'budget_sponsor':
            role, created = BudgetSponsor.objects.get_or_create(
                user=user,
                organizational_unit=unit,
                defaults={
                    'is_primary': data.get('is_primary', False),
                    'approval_limit': data.get('approval_limit'),
                    'sponsor_level': data.get('sponsor_level', 'level_1'),
                    'assigned_by': request.user
                }
            )
            serializer = BudgetSponsorSerializer(role)
        else:
            return Response(
                {'error': 'Invalid role_type'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not created:
            return Response(
                {'error': 'User already has this role in this unit'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update primary role if specified
        if data.get('is_primary', False):
            self._update_primary_role(unit, role_type, user)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'])
    def remove_role(self, request, pk=None):
        """Remove a role assignment from this unit"""
        unit = self.get_object()
        role_id = request.data.get('role_id')
        
        if not role_id:
            return Response(
                {'error': 'role_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Try to find the role in any of the role types
        role_models = [Recruiter, Manager, BudgetHolder, BudgetSponsor]
        role_deleted = False
        
        for model in role_models:
            try:
                role = model.objects.get(id=role_id, organizational_unit=unit)
                role.delete()
                role_deleted = True
                break
            except model.DoesNotExist:
                continue
        
        if not role_deleted:
            return Response(
                {'error': 'Role assignment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['patch'])
    def primary_roles(self, request, pk=None):
        """Update primary role assignments"""
        unit = self.get_object()
        data = request.data
        
        # Update primary roles
        if 'primary_recruiter_id' in data:
            unit.primary_recruiter_id = data['primary_recruiter_id']
        if 'primary_manager_id' in data:
            unit.primary_manager_id = data['primary_manager_id']
        if 'primary_budget_holder_id' in data:
            unit.primary_budget_holder_id = data['primary_budget_holder_id']
        if 'primary_budget_sponsor_id' in data:
            unit.primary_budget_sponsor_id = data['primary_budget_sponsor_id']
        
        unit.save()
        
        serializer = self.get_serializer(unit)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def update_headcount(self, request, pk=None):
        """Update current headcount with optional note"""
        unit = self.get_object()
        current_headcount = request.data.get('current_headcount')
        note = request.data.get('note', '')
        
        if current_headcount is None:
            return Response(
                {'error': 'current_headcount is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            current_headcount = int(current_headcount)
            if current_headcount < 0:
                raise ValueError("Headcount cannot be negative")
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid headcount value'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        unit.current_headcount = current_headcount
        unit.save()
        
        # You could log this change here if you have an audit system
        # AuditLog.objects.create(
        #     unit=unit,
        #     action='headcount_update',
        #     old_value=unit.current_headcount,
        #     new_value=current_headcount,
        #     note=note,
        #     updated_by=request.user
        # )
        
        serializer = self.get_serializer(unit)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def performance(self, request, pk=None):
        """Get performance metrics for a specific unit"""
        unit = self.get_object()
        period = request.query_params.get('period', '30d')
        
        performance_data = self._calculate_unit_performance(unit, period)
        return Response(performance_data)

    @action(detail=False, methods=['get'])
    def hierarchy(self, request):
        """Get organizational hierarchy"""
        include_performance = request.query_params.get('include_performance', 'false').lower() == 'true'
        max_depth = request.query_params.get('max_depth')
        
        # Get top-level departments
        departments = OrganizationalUnit.objects.filter(
            type='department', is_active=True
        ).prefetch_related('children__children')
        
        hierarchy_data = []
        for dept in departments:
            dept_data = self._build_hierarchy_node(dept, 0, max_depth, include_performance)
            hierarchy_data.append(dept_data)
        
        return Response(hierarchy_data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get comprehensive organizational unit statistics"""
        date_range = request.query_params.get('date_range', '30d')
        include_trends = request.query_params.get('include_trends', 'false').lower() == 'true'
        
        # Basic counts
        total_units = OrganizationalUnit.objects.filter(is_active=True).count()
        departments = OrganizationalUnit.objects.filter(type='department', is_active=True).count()
        divisions = OrganizationalUnit.objects.filter(type='division', is_active=True).count()
        units = OrganizationalUnit.objects.filter(type='unit', is_active=True).count()
        
        # Headcount statistics
        units_with_limits = OrganizationalUnit.objects.filter(
            is_active=True, headcount_limit__isnull=False
        )
        total_headcount = units_with_limits.aggregate(
            total=Sum('current_headcount')
        )['total'] or 0
        
        # Calculate average utilization
        utilization_data = units_with_limits.annotate(
            utilization=Case(
                When(headcount_limit=0, then=0),
                default=F('current_headcount') * 100.0 / F('headcount_limit'),
                output_field=IntegerField()
            )
        ).aggregate(
            avg_utilization=Avg('utilization'),
            over_capacity=Count('id', filter=Q(current_headcount__gt=F('headcount_limit')))
        )
        
        # Role assignment completeness
        units_with_all_roles = OrganizationalUnit.objects.filter(
            is_active=True,
            primary_recruiter__isnull=False,
            primary_manager__isnull=False,
            primary_budget_holder__isnull=False,
            primary_budget_sponsor__isnull=False
        ).count()
        
        # Recent updates (last 7 days)
        recent_cutoff = timezone.now() - timedelta(days=7)
        recent_updates = OrganizationalUnit.objects.filter(
            updated_at__gte=recent_cutoff
        ).count()
        
        # Budget utilization (placeholder - implement based on your budget model)
        budget_utilization = 75.0  # This should be calculated from actual budget data
        
        # Performance metrics
        performance_metrics = {
            'avg_performance_score': 78.5,  # Calculate from actual performance data
            'top_performing_units': OrganizationalUnit.objects.filter(is_active=True).count() // 4,
            'units_needing_attention': OrganizationalUnit.objects.filter(is_active=True).count() // 8
        }
        
        stats_data = {
            'total_units': total_units,
            'departments': departments,
            'divisions': divisions,
            'units': units,
            'total_headcount': total_headcount,
            'average_headcount_utilization': utilization_data['avg_utilization'] or 0,
            'units_over_capacity': utilization_data['over_capacity'],
            'units_with_all_roles_assigned': units_with_all_roles,
            'recent_updates': recent_updates,
            'budget_utilization': budget_utilization,
            'performance_metrics': performance_metrics
        }
        
        return Response(stats_data)

    @action(detail=False, methods=['get'])
    def headcount_report(self, request):
        """Generate comprehensive headcount report"""
        include_trends = request.query_params.get('include_trends', 'false').lower() == 'true'
        unit_type = request.query_params.get('unit_type')
        department = request.query_params.get('department')
        
        queryset = OrganizationalUnit.objects.filter(is_active=True)
        
        if unit_type:
            queryset = queryset.filter(type=unit_type)
        if department:
            queryset = queryset.filter(parent_id=department)
        
        queryset = queryset.select_related('parent', 'primary_manager').annotate(
            utilization_percentage=Case(
                When(headcount_limit=0, then=0),
                When(headcount_limit__isnull=True, then=0),
                default=F('current_headcount') * 100.0 / F('headcount_limit'),
                output_field=IntegerField()
            ),
            available_positions=Case(
                When(headcount_limit__isnull=True, then=0),
                default=F('headcount_limit') - F('current_headcount'),
                output_field=IntegerField()
            ),
            over_capacity=Case(
                When(current_headcount__gt=F('headcount_limit'), then=True),
                default=False,
                output_field=IntegerField()
            )
        )
        
        report_data = []
        total_headcount = 0
        total_capacity = 0
        units_over_capacity = 0
        
        for unit in queryset:
            # Build full path
            path_parts = [unit.name]
            parent = unit.parent
            while parent:
                path_parts.append(parent.name)
                parent = parent.parent
            full_path = ' > '.join(reversed(path_parts))
            
            unit_data = {
                'id': unit.id,
                'name': unit.name,
                'type': unit.type,
                'full_path': full_path,
                'current_headcount': unit.current_headcount,
                'headcount_limit': unit.headcount_limit or 0,
                'utilization_percentage': unit.utilization_percentage,
                'available_positions': unit.available_positions,
                'over_capacity': unit.over_capacity,
                'primary_manager': unit.primary_manager.get_full_name() if unit.primary_manager else None
            }
            
            if include_trends:
                # Add trend data (placeholder - implement based on historical data)
                unit_data['trend_data'] = {
                    'last_month': unit.current_headcount - 2,  # Example calculation
                    'last_quarter': unit.current_headcount - 5,
                    'growth_rate': 2.5  # Percentage growth
                }
            
            report_data.append(unit_data)
            total_headcount += unit.current_headcount
            total_capacity += unit.headcount_limit or 0
            if unit.over_capacity:
                units_over_capacity += 1
        
        # Summary statistics
        summary = {
            'total_headcount': total_headcount,
            'total_capacity': total_capacity,
            'overall_utilization': (total_headcount / total_capacity * 100) if total_capacity > 0 else 0,
            'units_over_capacity': units_over_capacity,
            'trending_up': len([u for u in report_data if u.get('trend_data', {}).get('growth_rate', 0) > 0]),
            'trending_down': len([u for u in report_data if u.get('trend_data', {}).get('growth_rate', 0) < 0])
        }
        
        return Response({
            'report': report_data,
            'summary': summary
        })

    @action(detail=False, methods=['post'])
    def bulk_assign_roles(self, request):
        """Bulk assign roles to multiple users/units"""
        assignments_data = request.data.get('assignments', [])
        
        if not assignments_data:
            return Response(
                {'error': 'assignments data is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_count = 0
        updated_count = 0
        errors = []
        
        for assignment in assignments_data:
            try:
                user_id = assignment.get('user_id')
                unit_id = assignment.get('unit_id')
                role_type = assignment.get('role_type')
                
                if not all([user_id, unit_id, role_type]):
                    errors.append(f"Missing required fields for assignment: {assignment}")
                    continue
                
                user = User.objects.get(id=user_id)
                unit = OrganizationalUnit.objects.get(id=unit_id)
                
                # Create the appropriate role
                role_created = False
                if role_type == 'recruiter':
                    role, created = Recruiter.objects.get_or_create(
                        user=user,
                        organizational_unit=unit,
                        defaults={
                            'is_primary': assignment.get('is_primary', False),
                            'specialization': assignment.get('specialization', ''),
                            'assigned_by': request.user
                        }
                    )
                    role_created = created
                elif role_type == 'manager':
                    role, created = Manager.objects.get_or_create(
                        user=user,
                        organizational_unit=unit,
                        defaults={
                            'is_primary': assignment.get('is_primary', False),
                            'manager_type': assignment.get('manager_type', 'line_manager'),
                            'assigned_by': request.user
                        }
                    )
                    role_created = created
                elif role_type == 'budget_holder':
                    role, created = BudgetHolder.objects.get_or_create(
                        user=user,
                        organizational_unit=unit,
                        defaults={
                            'is_primary': assignment.get('is_primary', False),
                            'budget_limit': assignment.get('budget_limit'),
                            'budget_type': assignment.get('budget_type', 'operational'),
                            'assigned_by': request.user
                        }
                    )
                    role_created = created
                elif role_type == 'budget_sponsor':
                    role, created = BudgetSponsor.objects.get_or_create(
                        user=user,
                        organizational_unit=unit,
                        defaults={
                            'is_primary': assignment.get('is_primary', False),
                            'approval_limit': assignment.get('approval_limit'),
                            'sponsor_level': assignment.get('sponsor_level', 'level_1'),
                            'assigned_by': request.user
                        }
                    )
                    role_created = created
                
                if role_created:
                    created_count += 1
                else:
                    updated_count += 1
                    
            except (User.DoesNotExist, OrganizationalUnit.DoesNotExist) as e:
                errors.append(f"Invalid user or unit ID in assignment: {assignment}")
            except Exception as e:
                errors.append(f"Error processing assignment {assignment}: {str(e)}")
        
        return Response({
            'message': f'Bulk assignment completed',
            'created': created_count,
            'updated': updated_count,
            'errors': errors
        })

    # Helper methods
    def _serialize_role_assignments(self, roles, role_type):
        """Serialize role assignments with consistent format"""
        role_data = []
        for role in roles:
            data = {
                'id': role.id,
                'user': {
                    'id': role.user.id,
                    'username': role.user.username,
                    'email': role.user.email,
                    'first_name': role.user.first_name,
                    'last_name': role.user.last_name,
                    'full_name': role.user.get_full_name(),
                    'profile_picture': getattr(role.user, 'profile_picture', None),
                    'department': getattr(role.user, 'department', None),
                    'position': getattr(role.user, 'position', None),
                },
                'role_type': role_type,
                'is_primary': role.is_primary,
                'is_active': role.is_active,
                'assigned_at': role.assigned_at.isoformat(),
                'assigned_by': {
                    'id': role.assigned_by.id,
                    'full_name': role.assigned_by.get_full_name()
                } if role.assigned_by else None,
                'permissions': self._get_role_permissions(role_type),
                'last_activity': None,  # Implement based on your activity tracking
            }
            
            # Add role-specific fields
            if role_type == 'recruiter' and hasattr(role, 'specialization'):
                data['specialization'] = role.specialization
            elif role_type == 'manager' and hasattr(role, 'manager_type'):
                data['manager_type'] = role.manager_type
            elif role_type == 'budget_holder':
                if hasattr(role, 'budget_limit'):
                    data['budget_limit'] = role.budget_limit
                if hasattr(role, 'budget_type'):
                    data['budget_type'] = role.budget_type
            elif role_type == 'budget_sponsor':
                if hasattr(role, 'approval_limit'):
                    data['approval_limit'] = role.approval_limit
                if hasattr(role, 'sponsor_level'):
                    data['sponsor_level'] = role.sponsor_level
            
            role_data.append(data)
        
        return role_data

    def _get_role_permissions(self, role_type):
        """Get permissions for each role type"""
        permissions_map = {
            'recruiter': [
                'view_candidates', 'create_job_posts', 'schedule_interviews',
                'manage_recruitment_pipeline', 'access_candidate_database'
            ],
            'manager': [
                'approve_hires', 'manage_team', 'conduct_reviews',
                'set_goals', 'approve_time_off', 'access_reports'
            ],
            'budget_holder': [
                'approve_budget_requests', 'view_budget_reports',
                'allocate_funds', 'track_expenses'
            ],
            'budget_sponsor': [
                'approve_major_expenses', 'strategic_budget_planning',
                'cross_department_budget_allocation', 'executive_reporting'
            ]
        }
        return permissions_map.get(role_type, [])

    def _calculate_unit_performance(self, unit, period='30d'):
        """Calculate performance metrics for a unit"""
        # This is a comprehensive performance calculation
        # You should implement this based on your specific metrics
        
        # Headcount efficiency (how well the unit uses its allocated headcount)
        headcount_efficiency = 0
        if unit.headcount_limit and unit.headcount_limit > 0:
            headcount_efficiency = min((unit.current_headcount / unit.headcount_limit) * 100, 100)
        elif unit.current_headcount > 0:
            headcount_efficiency = 85  # Default for units without limits
        
        # Role assignment completeness
        primary_roles = [
            unit.primary_recruiter,
            unit.primary_manager,
            unit.primary_budget_holder,
            unit.primary_budget_sponsor
        ]
        role_assignment_completeness = (sum(1 for role in primary_roles if role) / 4) * 100
        
        # Budget utilization (placeholder - implement based on actual budget tracking)
        budget_utilization = 75.0  # This should come from actual budget data
        
        # Recent activity score (placeholder - implement based on actual activity tracking)
        recent_activity_score = 80.0
        
        # Overall performance score (weighted average)
        performance_score = (
            headcount_efficiency * 0.3 +
            role_assignment_completeness * 0.3 +
            budget_utilization * 0.2 +
            recent_activity_score * 0.2
        )
        
        # Determine trends (placeholder - implement based on historical data)
        headcount_trend = 'stable'  # This should be calculated from historical data
        performance_trend = 'stable'
        
        # Generate recommendations
        recommendations = []
        if role_assignment_completeness < 100:
            missing_roles = []
            if not unit.primary_recruiter:
                missing_roles.append('Primary Recruiter')
            if not unit.primary_manager:
                missing_roles.append('Primary Manager')
            if not unit.primary_budget_holder:
                missing_roles.append('Primary Budget Holder')
            if not unit.primary_budget_sponsor:
                missing_roles.append('Primary Budget Sponsor')
            
            recommendations.append(f"Assign missing primary roles: {', '.join(missing_roles)}")
        
        if headcount_efficiency < 70:
            recommendations.append("Consider increasing headcount to improve efficiency")
        elif headcount_efficiency > 95:
            recommendations.append("Unit is at high capacity - monitor for potential overload")
        
        if budget_utilization < 60:
            recommendations.append("Budget utilization is low - review spending allocation")
        elif budget_utilization > 90:
            recommendations.append("Budget utilization is high - monitor for overspending")
        
        return {
            'unit_id': unit.id,
            'performance_score': round(performance_score, 1),
            'metrics': {
                'headcount_efficiency': round(headcount_efficiency, 1),
                'role_assignment_completeness': round(role_assignment_completeness, 1),
                'budget_utilization': round(budget_utilization, 1),
                'recent_activity_score': round(recent_activity_score, 1)
            },
            'trends': {
                'headcount_trend': headcount_trend,
                'performance_trend': performance_trend
            },
            'recommendations': recommendations
        }

    def _build_hierarchy_node(self, unit, depth, max_depth, include_performance):
        """Build a single node in the hierarchy tree"""
        node_data = {
            'id': unit.id,
            'name': unit.name,
            'type': unit.type,
            'code': unit.code,
            'current_headcount': unit.current_headcount,
            'headcount_limit': unit.headcount_limit,
            'children_count': unit.children.filter(is_active=True).count(),
            'depth': depth,
            'path': self._get_unit_path(unit)
        }
        
        if include_performance:
            node_data['performance'] = self._calculate_unit_performance(unit)
        
        # Add children if not at max depth
        if max_depth is None or depth < int(max_depth):
            children = unit.children.filter(is_active=True).order_by('name')
            if children.exists():
                node_data['children'] = [
                    self._build_hierarchy_node(child, depth + 1, max_depth, include_performance)
                    for child in children
                ]
        
        return node_data

    def _get_unit_path(self, unit):
        """Get the full path from root to this unit"""
        path = [unit.name]
        parent = unit.parent
        while parent:
            path.append(parent.name)
            parent = parent.parent
        return list(reversed(path))

    def _update_primary_role(self, unit, role_type, user):
        """Update the primary role assignment for a unit"""
        if role_type == 'recruiter':
            unit.primary_recruiter = user
        elif role_type == 'manager':
            unit.primary_manager = user
        elif role_type == 'budget_holder':
            unit.primary_budget_holder = user
        elif role_type == 'budget_sponsor':
            unit.primary_budget_sponsor = user
        
        unit.save()

class AvailableUsersViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for getting users available for role assignments"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = User.objects.filter(is_active=True)
        
        # Apply filters
        role_type = self.request.query_params.get('role_type')
        exclude_unit = self.request.query_params.get('exclude_unit')
        search = self.request.query_params.get('search')
        
        if exclude_unit:
            # Exclude users who already have this role type in the specified unit
            if role_type == 'recruiter':
                queryset = queryset.exclude(
                    recruiter_roles__organizational_unit_id=exclude_unit,
                    recruiter_roles__is_active=True
                )
            elif role_type == 'manager':
                queryset = queryset.exclude(
                    manager_roles__organizational_unit_id=exclude_unit,
                    manager_roles__is_active=True
                )
            elif role_type == 'budget_holder':
                queryset = queryset.exclude(
                    budget_holder_roles__organizational_unit_id=exclude_unit,
                    budget_holder_roles__is_active=True
                )
            elif role_type == 'budget_sponsor':
                queryset = queryset.exclude(
                    budget_sponsor_roles__organizational_unit_id=exclude_unit,
                    budget_sponsor_roles__is_active=True
                )
        
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(username__icontains=search)
            )
        
        return queryset.order_by('first_name', 'last_name')
    
    def list(self, request, *args, **kwargs):
        """Return available users with their current role information"""
        queryset = self.get_queryset()
        
        users_data = []
        for user in queryset[:100]:  # Limit to 100 users for performance
            # Get current roles for this user
            current_roles = []
            
            if user.recruiter_roles.filter(is_active=True).exists():
                current_roles.append('Recruiter')
            if user.manager_roles.filter(is_active=True).exists():
                current_roles.append('Manager')
            if user.budget_holder_roles.filter(is_active=True).exists():
                current_roles.append('Budget Holder')
            if user.budget_sponsor_roles.filter(is_active=True).exists():
                current_roles.append('Budget Sponsor')
            
            user_data = {
                'id': user.id,
                'full_name': user.get_full_name(),
                'email': user.email,
                'department': getattr(user, 'department', None),
                'position': getattr(user, 'position', None),
                'current_roles': current_roles
            }
            users_data.append(user_data)
        
        return Response(users_data)

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