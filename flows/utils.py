# flows/utils.py - Fixed condition evaluation
from datetime import timezone
from django.contrib.auth import get_user_model
from .models import Flow, FlowExecution, FlowExecutionStep
import logging

logger = logging.getLogger(__name__)
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
            'position_level': getattr(self.mpr, 'position_level', 'mid'),
            'salary_range': float(getattr(self.mpr, 'salary_range', 0)),
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
        """Evaluate conditions for a condition node - FIXED VERSION"""
        logger.info(f"Evaluating conditions for node {condition_node.name}")
        
        # Get conditions and groups from node properties
        properties = condition_node.properties or {}
        conditions_data = properties.get('conditions', [])
        groups_data = properties.get('groups', [])
        main_logic = properties.get('logicOperator', 'AND')
        
        logger.info(f"Found {len(conditions_data)} conditions and {len(groups_data)} groups")
        logger.info(f"Main logic operator: {main_logic}")
        
        if not conditions_data:
            logger.warning("No conditions found, taking 'false' path")
            return condition_node.outgoing_connections.filter(connection_type='false').first()
        
        # If we have conditions but no groups, create a default group
        if not groups_data:
            groups_data = [{'id': 1, 'logic': 'AND', 'parentGroup': None}]
        
        # Group conditions by group_id
        condition_groups = {}
        for condition in conditions_data:
            group_id = condition.get('group', 1)
            if group_id not in condition_groups:
                condition_groups[group_id] = []
            condition_groups[group_id].append(condition)
        
        # Evaluate each group
        group_results = {}
        for group in groups_data:
            group_id = group.get('id', 1)
            group_logic = group.get('logic', 'AND')
            group_conditions = condition_groups.get(group_id, [])
            
            logger.info(f"Evaluating group {group_id} with {len(group_conditions)} conditions using {group_logic} logic")
            
            if not group_conditions:
                group_results[group_id] = True
                continue
            
            # Evaluate conditions in the group
            results = []
            for condition in group_conditions:
                try:
                    result = self._evaluate_single_condition(condition)
                    results.append(result)
                    logger.info(f"Condition {condition.get('field')} {condition.get('operator')} {condition.get('value')} = {result}")
                except Exception as e:
                    logger.error(f"Error evaluating condition: {e}")
                    results.append(False)
            
            # Apply group logic
            if group_logic == 'AND':
                group_results[group_id] = all(results)
            else:  # OR
                group_results[group_id] = any(results)
            
            logger.info(f"Group {group_id} result: {group_results[group_id]}")
        
        # Apply main logic operator between groups
        if main_logic == 'AND':
            final_result = all(group_results.values()) if group_results else False
        else:  # OR
            final_result = any(group_results.values()) if group_results else False
        
        logger.info(f"Final condition result: {final_result}")
        
        # Return appropriate connection
        connection_type = 'true' if final_result else 'false'
        connection = condition_node.outgoing_connections.filter(connection_type=connection_type).first()
        
        if not connection:
            logger.warning(f"No {connection_type} connection found, looking for alternative")
            # Fallback to any available connection
            connection = condition_node.outgoing_connections.first()
        
        return connection
    
    def _evaluate_single_condition(self, condition):
        """Evaluate a single condition against MPR data - FIXED VERSION"""
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value', '')
        
        if not field or not operator:
            logger.warning(f"Invalid condition: field={field}, operator={operator}")
            return False
        
        context = self.execution.execution_context
        field_value = context.get(field)
        
        logger.debug(f"Evaluating: {field} ({field_value}) {operator} {value}")
        
        try:
            # Handle different operators
            if operator == 'equals':
                return str(field_value).lower() == str(value).lower()
            
            elif operator == 'not_equals':
                return str(field_value).lower() != str(value).lower()
            
            elif operator in ['greater_than', 'less_than', 'greater_equal', 'less_equal']:
                try:
                    field_num = float(field_value) if field_value is not None else 0
                    value_num = float(value) if value else 0
                    
                    if operator == 'greater_than':
                        return field_num > value_num
                    elif operator == 'less_than':
                        return field_num < value_num
                    elif operator == 'greater_equal':
                        return field_num >= value_num
                    elif operator == 'less_equal':
                        return field_num <= value_num
                except (ValueError, TypeError) as e:
                    logger.warning(f"Numeric comparison failed for {field_value} {operator} {value}: {e}")
                    return False
            
            elif operator == 'contains':
                field_str = str(field_value).lower() if field_value is not None else ''
                value_str = str(value).lower()
                return value_str in field_str
            
            elif operator == 'starts_with':
                field_str = str(field_value).lower() if field_value is not None else ''
                value_str = str(value).lower()
                return field_str.startswith(value_str)
            
            elif operator == 'ends_with':
                field_str = str(field_value).lower() if field_value is not None else ''
                value_str = str(value).lower()
                return field_str.endswith(value_str)
            
            elif operator == 'in_list':
                if not value:
                    return False
                values = [v.strip().lower() for v in str(value).split(',')]
                field_str = str(field_value).lower() if field_value is not None else ''
                return field_str in values
            
            elif operator == 'is_null':
                return field_value is None or field_value == '' or field_value == 'null'
            
            elif operator == 'is_not_null':
                return field_value is not None and field_value != '' and field_value != 'null'
            
            else:
                logger.warning(f"Unknown operator: {operator}")
                return False
                
        except Exception as e:
            logger.error(f"Error evaluating condition {field} {operator} {value}: {e}")
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
        logger.info(f"Notification sent: {subject} to {recipients}")
        logger.info(f"Message: {message}")
    
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