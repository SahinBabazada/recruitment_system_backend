# flows/views.py - Updated to fix templates permission
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Flow, FlowHistory, FlowExecution
from .serializers import (
    FlowListSerializer, FlowDetailSerializer, FlowCreateUpdateSerializer,
    FlowHistorySerializer, FlowExecutionSerializer, FlowActivateSerializer
)


class HasFlowPermission(permissions.BasePermission):
    """Custom permission class for flow operations"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Map actions to required permissions
        action_permissions = {
            'list': 'flow:view',
            'retrieve': 'flow:view',
            'create': 'flow:create',
            'update': 'flow:edit',
            'partial_update': 'flow:edit',
            'destroy': 'flow:delete',
            'activate': 'flow:activate',
            'history': 'flow:view',
            'statistics': 'flow:view',
            'duplicate': 'flow:create',
            'validate': 'flow:view',
            'templates': 'flow:view',  # Templates should be viewable by anyone who can view flows
        }
        
        required_permission = action_permissions.get(view.action, 'flow:view')
        
        # Check if user has the required permission
        return request.user.has_permission(required_permission)


class FlowViewSet(viewsets.ModelViewSet):
    """ViewSet for managing flows"""
    queryset = Flow.objects.all()
    permission_classes = [HasFlowPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'version']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'version', 'name']
    ordering = ['-version', '-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return FlowListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return FlowCreateUpdateSerializer
        else:
            return FlowDetailSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions"""
        queryset = super().get_queryset()
        
        # Add select_related and prefetch_related for optimization
        queryset = queryset.select_related(
            'created_by', 'activated_by'
        ).prefetch_related(
            'nodes', 'connections', 'history__user'
        )
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a flow (singleton pattern - deactivates others)"""
        flow = self.get_object()
        serializer = FlowActivateSerializer(data=request.data)
        
        if serializer.is_valid():
            if flow.status == 'active':
                return Response(
                    {'detail': 'Flow is already active'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if there's currently an active flow
            current_active = Flow.get_active_flow()
            
            with transaction.atomic():
                # Activate the flow (this will automatically deactivate others)
                flow.activate(request.user)
                
                return Response({
                    'detail': f'Flow "{flow.name}" v{flow.version} activated successfully',
                    'previous_active': current_active.name if current_active else None,
                    'flow': FlowDetailSerializer(flow, context={'request': request}).data
                })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """Get flow history"""
        flow = self.get_object()
        history = flow.history.all()
        
        # Apply pagination
        page = self.paginate_queryset(history)
        if page is not None:
            serializer = FlowHistorySerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = FlowHistorySerializer(history, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get flow statistics"""
        stats = {
            'total_flows': Flow.objects.count(),
            'active_flows': Flow.objects.filter(status='active').count(),
            'draft_flows': Flow.objects.filter(status='draft').count(),
            'archived_flows': Flow.objects.filter(status='archived').count(),
            'current_version': Flow.objects.order_by('-version').first().version if Flow.objects.exists() else 0,
            'active_flow': None
        }
        
        # Get active flow details
        active_flow = Flow.get_active_flow()
        if active_flow:
            stats['active_flow'] = {
                'id': active_flow.id,
                'name': active_flow.name,
                'version': active_flow.version,
                'node_count': active_flow.node_count,
                'connection_count': active_flow.connection_count,
                'activated_at': active_flow.activated_at,
                'activated_by': active_flow.activated_by.username if active_flow.activated_by else None
            }
        
        return Response(stats)
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Create a duplicate of an existing flow"""
        source_flow = self.get_object()
        
        # Get the flow data
        flow_data = FlowDetailSerializer(source_flow, context={'request': request}).data
        
        # Prepare data for new flow
        new_flow_data = {
            'name': f"{source_flow.name} (Copy)",
            'description': source_flow.description,
            'status': 'draft',
            'nodes': [],
            'connections': []
        }
        
        # Copy nodes
        for node in flow_data['nodes']:
            new_flow_data['nodes'].append({
                'id': node['node_id'],
                'type': node['node_type'],
                'position': node['position'],
                'properties': node['properties']
            })
        
        # Copy connections
        for connection in flow_data['connections']:
            new_flow_data['connections'].append({
                'id': connection['connection_id'],
                'startNodeId': connection['start_node_id'],
                'endNodeId': connection['end_node_id'],
                'type': connection['connection_type']
            })
        
        # Create the duplicate
        serializer = FlowCreateUpdateSerializer(data=new_flow_data, context={'request': request})
        if serializer.is_valid():
            new_flow = serializer.save()
            return Response(
                FlowDetailSerializer(new_flow, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def validate(self, request):
        """Validate flow data without saving"""
        serializer = FlowCreateUpdateSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            return Response({
                'valid': True,
                'message': 'Flow data is valid'
            })
        else:
            return Response({
                'valid': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def templates(self, request):
        """Get predefined flow templates - Allow anyone to access templates"""
        templates = [
            {
                'id': 'simple_approval',
                'name': 'Simple Approval',
                'description': 'Manager → Budget Holder approval flow',
                'nodes': [
                    {
                        'id': 'node_1',
                        'type': 'start',
                        'position': {'x': 100, 'y': 200},
                        'properties': {
                            'name': 'Flow Start',
                            'description': 'MPR submission begins here'
                        }
                    },
                    {
                        'id': 'node_2',
                        'type': 'approval',
                        'position': {'x': 350, 'y': 200},
                        'properties': {
                            'name': 'Manager Approval',
                            'approverType': 'manager',
                            'timeoutDays': 5,
                            'reminderDays': 3
                        }
                    },
                    {
                        'id': 'node_3',
                        'type': 'approval',
                        'position': {'x': 600, 'y': 200},
                        'properties': {
                            'name': 'Budget Approval',
                            'approverType': 'budget_holder',
                            'timeoutDays': 7,
                            'reminderDays': 5
                        }
                    },
                    {
                        'id': 'node_4',
                        'type': 'end',
                        'position': {'x': 850, 'y': 200},
                        'properties': {
                            'name': 'Flow End',
                            'finalStatus': 'approved'
                        }
                    }
                ],
                'connections': [
                    {
                        'id': 'conn_1',
                        'startNodeId': 'node_1',
                        'endNodeId': 'node_2',
                        'type': 'output'
                    },
                    {
                        'id': 'conn_2',
                        'startNodeId': 'node_2',
                        'endNodeId': 'node_3',
                        'type': 'output'
                    },
                    {
                        'id': 'conn_3',
                        'startNodeId': 'node_3',
                        'endNodeId': 'node_4',
                        'type': 'output'
                    }
                ]
            },
            {
                'id': 'complex_conditional',
                'name': 'Complex Conditional Flow',
                'description': 'Multi-level approval with conditions',
                'nodes': [
                    {
                        'id': 'node_1',
                        'type': 'start',
                        'position': {'x': 100, 'y': 250},
                        'properties': {
                            'name': 'Flow Start',
                            'description': 'MPR submission begins here'
                        }
                    },
                    {
                        'id': 'node_2',
                        'type': 'condition',
                        'position': {'x': 300, 'y': 250},
                        'properties': {
                            'name': 'Priority Check',
                            'logicOperator': 'OR',
                            'conditions': [
                                {
                                    'id': 1,
                                    'field': 'priority',
                                    'operator': 'equals',
                                    'value': 'urgent',
                                    'group': 1
                                },
                                {
                                    'id': 2,
                                    'field': 'budget_amount',
                                    'operator': 'greater_than',
                                    'value': '50000',
                                    'group': 2
                                }
                            ],
                            'groups': [
                                {'id': 1, 'logic': 'AND', 'parentGroup': None},
                                {'id': 2, 'logic': 'AND', 'parentGroup': None}
                            ]
                        }
                    },
                    {
                        'id': 'node_3',
                        'type': 'approval',
                        'position': {'x': 200, 'y': 150},
                        'properties': {
                            'name': 'Executive Approval',
                            'approverType': 'budget_sponsor',
                            'timeoutDays': 3,
                            'reminderDays': 2
                        }
                    },
                    {
                        'id': 'node_4',
                        'type': 'approval',
                        'position': {'x': 200, 'y': 350},
                        'properties': {
                            'name': 'Manager Approval',
                            'approverType': 'manager',
                            'timeoutDays': 5,
                            'reminderDays': 3
                        }
                    },
                    {
                        'id': 'node_5',
                        'type': 'notification',
                        'position': {'x': 500, 'y': 250},
                        'properties': {
                            'name': 'Notify All',
                            'recipients': 'creator,manager,recruiter',
                            'subject': 'MPR Approved: {position}',
                            'message': 'The MPR for {position} has been approved and is ready for next steps.'
                        }
                    },
                    {
                        'id': 'node_6',
                        'type': 'end',
                        'position': {'x': 700, 'y': 250},
                        'properties': {
                            'name': 'Flow End',
                            'finalStatus': 'approved'
                        }
                    }
                ],
                'connections': [
                    {
                        'id': 'conn_1',
                        'startNodeId': 'node_1',
                        'endNodeId': 'node_2',
                        'type': 'output'
                    },
                    {
                        'id': 'conn_2',
                        'startNodeId': 'node_2',
                        'endNodeId': 'node_3',
                        'type': 'true'
                    },
                    {
                        'id': 'conn_3',
                        'startNodeId': 'node_2',
                        'endNodeId': 'node_4',
                        'type': 'false'
                    },
                    {
                        'id': 'conn_4',
                        'startNodeId': 'node_3',
                        'endNodeId': 'node_5',
                        'type': 'output'
                    },
                    {
                        'id': 'conn_5',
                        'startNodeId': 'node_4',
                        'endNodeId': 'node_5',
                        'type': 'output'
                    },
                    {
                        'id': 'conn_6',
                        'startNodeId': 'node_5',
                        'endNodeId': 'node_6',
                        'type': 'output'
                    }
                ]
            }
        ]
        
        return Response(templates)
    
    def destroy(self, request, *args, **kwargs):
        """Override destroy to prevent deletion of active flows"""
        instance = self.get_object()
        
        if instance.status == 'active':
            return Response(
                {'detail': 'Cannot delete active flow. Archive it first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create history entry before deletion
        FlowHistory.objects.create(
            flow=instance,
            action='deleted',
            user=request.user,
            details=f"Flow '{instance.name}' v{instance.version} deleted",
            previous_state={
                'name': instance.name,
                'version': instance.version,
                'node_count': instance.node_count,
                'connection_count': instance.connection_count
            }
        )
        
        return super().destroy(request, *args, **kwargs)


class FlowExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing flow executions"""
    queryset = FlowExecution.objects.all()
    serializer_class = FlowExecutionSerializer
    permission_classes = [HasFlowPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'flow']
    search_fields = ['mpr__position_title']
    ordering_fields = ['started_at', 'completed_at']
    ordering = ['-started_at']
    
    def get_queryset(self):
        """Filter queryset based on user permissions"""
        queryset = super().get_queryset()
        
        # Add optimizations
        queryset = queryset.select_related(
            'flow', 'mpr', 'current_node'
        ).prefetch_related(
            'steps__node', 'steps__assigned_to', 'steps__approved_by'
        )
        
        return queryset