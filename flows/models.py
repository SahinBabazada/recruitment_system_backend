# flows/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
import json

User = get_user_model()

class Flow(models.Model):
    """
    Main Flow model - Singleton pattern implementation
    Only one active flow allowed per organization
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_flows')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    activated_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='activated_flows')
    
    # Statistics
    node_count = models.PositiveIntegerField(default=0)
    connection_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'flows'
        ordering = ['-version', '-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['version']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            # Ensure only one active flow at a time
            models.UniqueConstraint(
                fields=['status'],
                condition=models.Q(status='active'),
                name='unique_active_flow'
            )
        ]
    
    def __str__(self):
        return f"{self.name} (v{self.version}) - {self.status}"
    
    def save(self, *args, **kwargs):
        if self.status == 'active':
            # Deactivate all other flows when activating this one
            Flow.objects.filter(status='active').exclude(pk=self.pk).update(
                status='archived',
                updated_at=timezone.now()
            )
            if not self.activated_at:
                self.activated_at = timezone.now()
        
        # Auto-increment version for new flows
        if not self.pk:
            last_flow = Flow.objects.order_by('-version').first()
            if last_flow:
                self.version = last_flow.version + 1
        
        super().save(*args, **kwargs)
    
    @classmethod
    def get_active_flow(cls):
        """Get the currently active flow"""
        return cls.objects.filter(status='active').first()
    
    @classmethod
    def create_new_version(cls, user, **kwargs):
        """Create a new version of the flow"""
        # Get the latest version
        latest = cls.objects.order_by('-version').first()
        new_version = (latest.version + 1) if latest else 1
        
        # Create new flow version
        new_flow = cls.objects.create(
            version=new_version,
            created_by=user,
            **kwargs
        )
        return new_flow
    
    def activate(self, user):
        """Activate this flow version"""
        self.status = 'active'
        self.activated_by = user
        self.activated_at = timezone.now()
        self.save()
        
        # Create history entry
        FlowHistory.objects.create(
            flow=self,
            action='activated',
            user=user,
            details=f"Flow v{self.version} activated"
        )
    
    def update_statistics(self):
        """Update node and connection counts"""
        self.node_count = self.nodes.count()
        self.connection_count = self.connections.count()
        self.save(update_fields=['node_count', 'connection_count', 'updated_at'])


class FlowNode(models.Model):
    """
    Individual nodes in a flow
    """
    NODE_TYPES = [
        ('start', 'Start Node'),
        ('approval', 'Approval Stage'),
        ('condition', 'Condition Check'),
        ('notification', 'Notification'),
        ('end', 'End Node'),
    ]
    
    flow = models.ForeignKey(Flow, on_delete=models.CASCADE, related_name='nodes')
    node_id = models.CharField(max_length=50)  # Frontend-generated ID like 'node_1'
    node_type = models.CharField(max_length=20, choices=NODE_TYPES)
    name = models.CharField(max_length=200)
    
    # Position on canvas
    position_x = models.FloatField()
    position_y = models.FloatField()
    
    # Node configuration (JSON field for flexibility)
    properties = models.JSONField(default=dict)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'flow_nodes'
        unique_together = ['flow', 'node_id']
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['flow', 'node_type']),
            models.Index(fields=['node_id']),
        ]
    
    def __str__(self):
        return f"{self.flow.name} - {self.name} ({self.node_type})"
    
    def clean(self):
        """Validate node properties based on type"""
        if self.node_type == 'approval':
            required_fields = ['approverType', 'timeoutDays']
            for field in required_fields:
                if field not in self.properties:
                    raise ValidationError(f"Approval node requires '{field}' property")
        
        elif self.node_type == 'condition':
            if 'conditions' not in self.properties or not self.properties['conditions']:
                raise ValidationError("Condition node requires at least one condition")
        
        elif self.node_type == 'notification':
            required_fields = ['recipients', 'message']
            for field in required_fields:
                if field not in self.properties:
                    raise ValidationError(f"Notification node requires '{field}' property")


class FlowConnection(models.Model):
    """
    Connections between flow nodes
    """
    CONNECTION_TYPES = [
        ('output', 'Standard Output'),
        ('true', 'Condition True'),
        ('false', 'Condition False'),
    ]
    
    flow = models.ForeignKey(Flow, on_delete=models.CASCADE, related_name='connections')
    connection_id = models.CharField(max_length=50)  # Frontend-generated ID
    
    # Source and target nodes
    start_node = models.ForeignKey(FlowNode, on_delete=models.CASCADE, related_name='outgoing_connections')
    end_node = models.ForeignKey(FlowNode, on_delete=models.CASCADE, related_name='incoming_connections')
    
    # Connection type (for conditional branches)
    connection_type = models.CharField(max_length=20, choices=CONNECTION_TYPES, default='output')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'flow_connections'
        unique_together = ['flow', 'connection_id']
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['flow']),
            models.Index(fields=['start_node']),
            models.Index(fields=['end_node']),
        ]
    
    def __str__(self):
        return f"{self.start_node.name} -> {self.end_node.name} ({self.connection_type})"
    
    def clean(self):
        """Validate connection logic"""
        # Prevent self-connections
        if self.start_node == self.end_node:
            raise ValidationError("Node cannot connect to itself")
        
        # Ensure nodes belong to the same flow
        if self.start_node.flow != self.end_node.flow:
            raise ValidationError("Connected nodes must belong to the same flow")
        
        # Validate connection types based on source node type
        if self.start_node.node_type == 'condition':
            if self.connection_type not in ['true', 'false']:
                raise ValidationError("Condition nodes must use 'true' or 'false' connection types")
        else:
            if self.connection_type != 'output':
                raise ValidationError("Non-condition nodes must use 'output' connection type")


class FlowCondition(models.Model):
    """
    Individual conditions for condition nodes
    """
    OPERATORS = [
        ('equals', 'Equals'),
        ('not_equals', 'Not Equals'),
        ('greater_than', 'Greater Than'),
        ('less_than', 'Less Than'),
        ('greater_equal', 'Greater or Equal'),
        ('less_equal', 'Less or Equal'),
        ('contains', 'Contains'),
        ('starts_with', 'Starts With'),
        ('ends_with', 'Ends With'),
        ('in_list', 'In List'),
        ('is_null', 'Is Empty'),
        ('is_not_null', 'Is Not Empty'),
    ]
    
    FIELDS = [
        ('priority', 'Priority'),
        ('department', 'Department'),
        ('budget_amount', 'Budget Amount'),
        ('employment_type', 'Employment Type'),
        ('location', 'Location'),
        ('hiring_reason', 'Hiring Reason'),
        ('desired_start_date', 'Start Date'),
        ('position_level', 'Position Level'),
        ('salary_range', 'Salary Range'),
    ]
    
    node = models.ForeignKey(FlowNode, on_delete=models.CASCADE, related_name='conditions')
    condition_id = models.PositiveIntegerField()  # ID within the node
    field = models.CharField(max_length=50, choices=FIELDS)
    operator = models.CharField(max_length=20, choices=OPERATORS)
    value = models.CharField(max_length=500, blank=True)
    group_id = models.PositiveIntegerField(default=1)  # For grouping conditions
    
    class Meta:
        db_table = 'flow_conditions'
        unique_together = ['node', 'condition_id']
        ordering = ['group_id', 'condition_id']
    
    def __str__(self):
        return f"{self.field} {self.operator} {self.value}"


class FlowConditionGroup(models.Model):
    """
    Groups for organizing conditions with AND/OR logic
    """
    LOGIC_OPERATORS = [
        ('AND', 'AND'),
        ('OR', 'OR'),
    ]
    
    node = models.ForeignKey(FlowNode, on_delete=models.CASCADE, related_name='condition_groups')
    group_id = models.PositiveIntegerField()
    logic_operator = models.CharField(max_length=3, choices=LOGIC_OPERATORS, default='AND')
    parent_group = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'flow_condition_groups'
        unique_together = ['node', 'group_id']
        ordering = ['group_id']
    
    def __str__(self):
        return f"Group {self.group_id} - {self.logic_operator}"


class FlowHistory(models.Model):
    """
    Track all changes to flows for audit purposes
    """
    ACTIONS = [
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('activated', 'Activated'),
        ('archived', 'Archived'),
        ('node_added', 'Node Added'),
        ('node_updated', 'Node Updated'),
        ('node_deleted', 'Node Deleted'),
        ('connection_added', 'Connection Added'),
        ('connection_deleted', 'Connection Deleted'),
    ]
    
    flow = models.ForeignKey(Flow, on_delete=models.CASCADE, related_name='history')
    action = models.CharField(max_length=20, choices=ACTIONS)
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='flow_actions')
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True)
    
    # Store the state before change (for rollback purposes)
    previous_state = models.JSONField(null=True, blank=True)
    
    class Meta:
        db_table = 'flow_history'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['flow', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action']),
        ]
    
    def __str__(self):
        return f"{self.flow.name} - {self.action} by {self.user.username} at {self.timestamp}"


class FlowExecution(models.Model):
    """
    Track execution of flows for MPRs
    """
    EXECUTION_STATUS = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    flow = models.ForeignKey(Flow, on_delete=models.PROTECT, related_name='executions')
    mpr = models.ForeignKey('mpr.MPR', on_delete=models.CASCADE, related_name='flow_executions')
    
    # Current state
    current_node = models.ForeignKey(FlowNode, on_delete=models.PROTECT, null=True, blank=True)
    status = models.CharField(max_length=20, choices=EXECUTION_STATUS, default='pending')
    
    # Execution metadata
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Execution context (store MPR data snapshot)
    execution_context = models.JSONField(default=dict)
    
    class Meta:
        db_table = 'flow_executions'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['flow', 'status']),
            models.Index(fields=['mpr']),
            models.Index(fields=['status', '-started_at']),
        ]
    
    def __str__(self):
        return f"Flow {self.flow.name} for MPR {self.mpr.id} - {self.status}"


class FlowExecutionStep(models.Model):
    """
    Individual steps in flow execution
    """
    STEP_STATUS = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('skipped', 'Skipped'),
        ('failed', 'Failed'),
    ]
    
    execution = models.ForeignKey(FlowExecution, on_delete=models.CASCADE, related_name='steps')
    node = models.ForeignKey(FlowNode, on_delete=models.PROTECT)
    
    # Step metadata
    step_order = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STEP_STATUS, default='pending')
    
    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Step-specific data
    input_data = models.JSONField(default=dict)
    output_data = models.JSONField(default=dict)
    error_message = models.TextField(blank=True)
    
    # For approval nodes
    assigned_to = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='approved_steps')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'flow_execution_steps'
        unique_together = ['execution', 'step_order']
        ordering = ['step_order']
        indexes = [
            models.Index(fields=['execution', 'status']),
            models.Index(fields=['node']),
            models.Index(fields=['assigned_to', 'status']),
        ]
    
    def __str__(self):
        return f"Step {self.step_order}: {self.node.name} - {self.status}"