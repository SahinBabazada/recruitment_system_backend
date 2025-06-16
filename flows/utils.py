# flows/utils.py
from datetime import timezone
from django.contrib.auth import get_user_model
from .models import Flow, FlowExecution, FlowExecutionStep

User = get_user_model()

def create_flow_permissions():
    """Create flow-related permissions"""
    try:
        from permissions.models import Permission
        
        flow_permissions = [
            ('flow:view', 'View flows', 'flow', 'view'),
            ('flow:create', 'Create flows', 'flow', 'create'),
            ('flow:edit', 'Edit flows', 'flow', 'edit'),
            ('flow:delete', 'Delete flows', 'flow', 'delete'),
            ('flow:activate', 'Activate flows', 'flow', 'activate'),
            ('flow:execute', 'Execute flows', 'flow', 'execute'),
        ]
        
        created_count = 0
        for name, description, module, action in flow_permissions:
            permission, created = Permission.objects.get_or_create(
                name=name,
                defaults={
                    'description': description,
                    'module': module,
                    'action': action
                }
            )
            if created:
                created_count += 1
                print(f"Created permission: {name}")
        
        print(f"Flow permissions setup complete. Created {created_count} new permissions.")
        
    except ImportError:
        print("Permissions app not available. Skipping flow permissions creation.")


class FlowExecutor:
    """Class for executing flows on MPRs"""
    
    def __init__(self, flow, mpr):
        self.flow = flow
        self.mpr = mpr
        self.execution = None
    
    def start_execution(self):
        """Start flow execution for the MPR"""
        if not self.flow or self.flow.status != 'active':
            raise ValueError("Cannot execute inactive flow")
        
        # Create execution record
        self.execution = FlowExecution.objects.create(
            flow=self.flow,
            mpr=self.mpr,
            execution_context=self._build_execution_context()
        )
        
        # Find start node
        start_node = self.flow.nodes.filter(node_type='start').first()
        if not start_node:
            raise ValueError("Flow has no start node")
        
        # Create first step
        step = FlowExecutionStep.objects.create(
            execution=self.execution,
            node=start_node,
            step_order=1,
            status='completed',
            input_data={},
            output_data={'mpr_id': self.mpr.id}
        )
        
        # Move to next node
        self._process_next_step(start_node, step)
        
        return self.execution
    
    def _build_execution_context(self):
        """Build execution context from MPR data"""
        return {
            'mpr_id': self.mpr.id,
            'priority': getattr(self.mpr, 'priority', 'normal'),
            'department': self.mpr.department.name if hasattr(self.mpr, 'department') and self.mpr.department else None,
            'budget_amount': float(getattr(self.mpr, 'budget_amount', 0)),
            'employment_type': self.mpr.employment_type.name if hasattr(self.mpr, 'employment_type') and self.mpr.employment_type else None,
            'location': self.mpr.location.name if hasattr(self.mpr, 'location') and self.mpr.location else None,
            'hiring_reason': self.mpr.hiring_reason.name if hasattr(self.mpr, 'hiring_reason') and self.mpr.hiring_reason else None,
            'position_title': getattr(self.mpr, 'position_title', ''),
            'created_at': self.mpr.created_at.isoformat() if hasattr(self.mpr, 'created_at') else None,
        }
    
    def _process_next_step(self, current_node, current_step):
        """Process the next step in the flow"""
        # Find outgoing connections
        connections = current_node.outgoing_connections.all()
        
        if not connections:
            # End of flow
            self.execution.status = 'completed'
            self.execution.save()
            return
        
        # For condition nodes, evaluate conditions
        if current_node.node_type == 'condition':
            next_connection = self._evaluate_conditions(current_node)
        else:
            # For other nodes, take the first (and usually only) connection
            next_connection = connections.first()
        
        if next_connection:
            next_node = next_connection.end_node
            
            # Create next step
            next_step = FlowExecutionStep.objects.create(
                execution=self.execution,
                node=next_node,
                step_order=current_step.step_order + 1,
                status='pending',
                input_data=current_step.output_data
            )
            
            # Update execution current node
            self.execution.current_node = next_node
            self.execution.status = 'in_progress'
            self.execution.save()
            
            # Process the step based on node type
            self._process_step(next_step)
    
    def _evaluate_conditions(self, condition_node):
        """Evaluate conditions for a condition node"""
        conditions = condition_node.conditions.all()
        groups = condition_node.condition_groups.all()
        
        if not conditions:
            # No conditions, take 'false' path
            return condition_node.outgoing_connections.filter(connection_type='false').first()
        
        # Group conditions by group_id
        condition_groups = {}
        for condition in conditions:
            if condition.group_id not in condition_groups:
                condition_groups[condition.group_id] = []
            condition_groups[condition.group_id].append(condition)
        
        # Evaluate each group
        group_results = {}
        for group in groups:
            group_conditions = condition_groups.get(group.group_id, [])
            if not group_conditions:
                group_results[group.group_id] = True
                continue
            
            # Evaluate conditions in the group
            results = []
            for condition in group_conditions:
                result = self._evaluate_single_condition(condition)
                results.append(result)
            
            # Apply group logic
            if group.logic_operator == 'AND':
                group_results[group.group_id] = all(results)
            else:  # OR
                group_results[group.group_id] = any(results)
        
        # Apply main logic operator
        main_logic = condition_node.properties.get('logicOperator', 'AND')
        if main_logic == 'AND':
            final_result = all(group_results.values())
        else:  # OR
            final_result = any(group_results.values())
        
        # Return appropriate connection
        connection_type = 'true' if final_result else 'false'
        return condition_node.outgoing_connections.filter(connection_type=connection_type).first()
    
    def _evaluate_single_condition(self, condition):
        """Evaluate a single condition against MPR data"""
        context = self.execution.execution_context
        field_value = context.get(condition.field)
        condition_value = condition.value
        
        # Handle different operators
        if condition.operator == 'equals':
            return str(field_value) == str(condition_value)
        elif condition.operator == 'not_equals':
            return str(field_value) != str(condition_value)
        elif condition.operator == 'greater_than':
            try:
                return float(field_value) > float(condition_value)
            except (ValueError, TypeError):
                return False
        elif condition.operator == 'less_than':
            try:
                return float(field_value) < float(condition_value)
            except (ValueError, TypeError):
                return False
        elif condition.operator == 'greater_equal':
            try:
                return float(field_value) >= float(condition_value)
            except (ValueError, TypeError):
                return False
        elif condition.operator == 'less_equal':
            try:
                return float(field_value) <= float(condition_value)
            except (ValueError, TypeError):
                return False
        elif condition.operator == 'contains':
            return condition_value.lower() in str(field_value).lower()
        elif condition.operator == 'starts_with':
            return str(field_value).lower().startswith(condition_value.lower())
        elif condition.operator == 'ends_with':
            return str(field_value).lower().endswith(condition_value.lower())
        elif condition.operator == 'in_list':
            values = [v.strip() for v in condition_value.split(',')]
            return str(field_value) in values
        elif condition.operator == 'is_null':
            return field_value is None or field_value == ''
        elif condition.operator == 'is_not_null':
            return field_value is not None and field_value != ''
        
        return False
    
    def _process_step(self, step):
        """Process a step based on its node type"""
        node = step.node
        
        if node.node_type == 'start':
            # Start nodes are automatically completed
            step.status = 'completed'
            step.output_data = {'started': True}
            step.save()
            self._process_next_step(node, step)
        
        elif node.node_type == 'approval':
            # Approval nodes require user action
            self._setup_approval_step(step)
        
        elif node.node_type == 'condition':
            # Condition nodes are automatically evaluated
            step.status = 'completed'
            step.output_data = {'evaluated': True}
            step.save()
            self._process_next_step(node, step)
        
        elif node.node_type == 'notification':
            # Notification nodes send notifications and continue
            self._send_notification(step)
            step.status = 'completed'
            step.output_data = {'notification_sent': True}
            step.save()
            self._process_next_step(node, step)
        
        elif node.node_type == 'end':
            # End nodes complete the flow
            step.status = 'completed'
            step.output_data = {'flow_completed': True}
            step.save()
            
            self.execution.status = 'completed'
            self.execution.completed_at = timezone.now()
            self.execution.save()
    
    def _setup_approval_step(self, step):
        """Setup approval step with proper assignee"""
        node = step.node
        properties = node.properties
        approver_type = properties.get('approverType', 'manager')
        
        # Find the appropriate approver based on type
        assigned_user = self._find_approver(approver_type)
        
        if assigned_user:
            step.assigned_to = assigned_user
            step.status = 'in_progress'
            step.save()
            
            # Here you would typically send a notification to the approver
            # This could integrate with your email service
        else:
            step.status = 'failed'
            step.error_message = f"No {approver_type} found for approval"
            step.save()
    
    def _find_approver(self, approver_type):
        """Find the appropriate approver based on type"""
        # This is a simplified implementation
        # In reality, you'd look up the appropriate approver based on:
        # - MPR department/organizational unit
        # - Approver type (manager, budget_holder, etc.)
        # - Active status and availability
        
        if approver_type == 'manager':
            # Find manager for the MPR's department
            if hasattr(self.mpr, 'department') and self.mpr.department:
                manager = self.mpr.department.managers.filter(is_active=True).first()
                return manager.user if manager else None
        
        elif approver_type == 'budget_holder':
            # Find budget holder for the department
            if hasattr(self.mpr, 'department') and self.mpr.department:
                budget_holder = self.mpr.department.budget_holders.filter(is_active=True).first()
                return budget_holder.user if budget_holder else None
        
        # Add more approver type logic as needed
        return None
    
    def _send_notification(self, step):
        """Send notification for notification nodes"""
        node = step.node
        properties = node.properties
        
        recipients = properties.get('recipients', 'creator')
        message = properties.get('message', 'MPR status updated')
        subject = properties.get('subject', 'MPR Notification')
        
        # Here you would integrate with your email service
        # For now, we'll just log the notification
        print(f"Notification sent: {subject} to {recipients}")
        print(f"Message: {message}")
    
    def approve_step(self, step_id, user, approved=True, comments=""):
        """Approve or reject an approval step"""
        step = FlowExecutionStep.objects.get(id=step_id, execution=self.execution)
        
        if step.status != 'in_progress':
            raise ValueError("Step is not pending approval")
        
        if step.assigned_to != user:
            # Check if user has permission to approve on behalf of assigned user
            if not user.has_permission('flow:approve_on_behalf'):
                raise ValueError("User not authorized to approve this step")
        
        step.approved_by = user
        step.approved_at = timezone.now()
        
        if approved:
            step.status = 'completed'
            step.output_data = {
                'approved': True,
                'approved_by': user.username,
                'comments': comments
            }
            
            # Continue to next step
            self._process_next_step(step.node, step)
        else:
            step.status = 'failed'
            step.error_message = f"Rejected by {user.username}: {comments}"
            
            # End the execution
            self.execution.status = 'failed'
            self.execution.error_message = f"Flow rejected at step {step.step_order}"
            self.execution.save()
        
        step.save()
        return step


def execute_flow_for_mpr(mpr):
    """Execute the active flow for an MPR"""
    active_flow = Flow.get_active_flow()
    
    if not active_flow:
        raise ValueError("No active flow found")
    
    executor = FlowExecutor(active_flow, mpr)
    return executor.start_execution()


def get_pending_approvals_for_user(user):
    """Get pending approval steps for a user"""
    return FlowExecutionStep.objects.filter(
        assigned_to=user,
        status='in_progress'
    ).select_related(
        'execution__flow', 'execution__mpr', 'node'
    ).order_by('-execution__started_at')