# flows/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import (
    Flow, FlowNode, FlowConnection, FlowCondition, FlowConditionGroup,
    FlowHistory, FlowExecution, FlowExecutionStep
)

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class FlowConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlowCondition
        fields = [
            'condition_id', 'field', 'operator', 'value', 'group_id'
        ]


class FlowConditionGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlowConditionGroup
        fields = ['group_id', 'logic_operator', 'parent_group']


class FlowNodeSerializer(serializers.ModelSerializer):
    conditions = FlowConditionSerializer(many=True, read_only=True)
    condition_groups = FlowConditionGroupSerializer(many=True, read_only=True)
    position = serializers.SerializerMethodField()
    
    class Meta:
        model = FlowNode
        fields = [
            'id', 'node_id', 'node_type', 'name', 'position', 'properties',
            'conditions', 'condition_groups', 'created_at', 'updated_at'
        ]
    
    def get_position(self, obj):
        return {'x': obj.position_x, 'y': obj.position_y}


class FlowConnectionSerializer(serializers.ModelSerializer):
    start_node_id = serializers.CharField(source='start_node.node_id', read_only=True)
    end_node_id = serializers.CharField(source='end_node.node_id', read_only=True)
    
    class Meta:
        model = FlowConnection
        fields = [
            'id', 'connection_id', 'start_node_id', 'end_node_id', 
            'connection_type', 'created_at'
        ]


class FlowHistorySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = FlowHistory
        fields = [
            'id', 'action', 'user', 'timestamp', 'details', 'previous_state'
        ]


class FlowListSerializer(serializers.ModelSerializer):
    """Serializer for flow list view with minimal fields"""
    created_by = UserSerializer(read_only=True)
    activated_by = UserSerializer(read_only=True)
    is_active = serializers.SerializerMethodField()
    
    class Meta:
        model = Flow
        fields = [
            'id', 'name', 'description', 'version', 'status', 'node_count',
            'connection_count', 'created_by', 'activated_by', 'created_at',
            'updated_at', 'activated_at', 'is_active'
        ]
    
    def get_is_active(self, obj):
        return obj.status == 'active'


class FlowDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed flow view with all related data"""
    nodes = FlowNodeSerializer(many=True, read_only=True)
    connections = FlowConnectionSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)
    activated_by = UserSerializer(read_only=True)
    history = FlowHistorySerializer(many=True, read_only=True)
    is_active = serializers.SerializerMethodField()
    
    class Meta:
        model = Flow
        fields = [
            'id', 'name', 'description', 'version', 'status', 'node_count',
            'connection_count', 'created_by', 'activated_by', 'created_at',
            'updated_at', 'activated_at', 'is_active', 'nodes', 'connections', 'history'
        ]
    
    def get_is_active(self, obj):
        return obj.status == 'active'


class FlowCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating flows with nested data"""
    nodes = serializers.ListField(child=serializers.DictField(), write_only=True, required=False)
    connections = serializers.ListField(child=serializers.DictField(), write_only=True, required=False)
    
    class Meta:
        model = Flow
        fields = [
            'id', 'name', 'description', 'status', 'nodes', 'connections'
        ]
        read_only_fields = ['id', 'version']
    
    def validate(self, data):
        """Validate flow data"""
        nodes = data.get('nodes', [])
        connections = data.get('connections', [])
        
        if nodes:
            # Validate required node types
            node_types = [node.get('type') for node in nodes]
            if 'start' not in node_types:
                raise serializers.ValidationError("Flow must have at least one start node")
            if 'end' not in node_types:
                raise serializers.ValidationError("Flow must have at least one end node")
            
            # Validate node IDs are unique
            node_ids = [node.get('id') for node in nodes]
            if len(node_ids) != len(set(node_ids)):
                raise serializers.ValidationError("Node IDs must be unique")
        
        if connections:
            # Validate connection references
            node_ids = [node.get('id') for node in nodes]
            for conn in connections:
                start_id = conn.get('startNodeId')
                end_id = conn.get('endNodeId')
                
                if start_id not in node_ids:
                    raise serializers.ValidationError(f"Connection references unknown start node: {start_id}")
                if end_id not in node_ids:
                    raise serializers.ValidationError(f"Connection references unknown end node: {end_id}")
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        """Create flow with nested nodes and connections"""
        nodes_data = validated_data.pop('nodes', [])
        connections_data = validated_data.pop('connections', [])
        
        # Set created_by from request user
        validated_data['created_by'] = self.context['request'].user
        
        # Create flow
        flow = Flow.objects.create(**validated_data)
        
        # Create nodes
        self._create_nodes(flow, nodes_data)
        
        # Create connections
        self._create_connections(flow, connections_data)
        
        # Update statistics
        flow.update_statistics()
        
        # Create history entry
        FlowHistory.objects.create(
            flow=flow,
            action='created',
            user=self.context['request'].user,
            details=f"Flow '{flow.name}' created with {len(nodes_data)} nodes and {len(connections_data)} connections"
        )
        
        return flow
    
    @transaction.atomic
    def update(self, instance, validated_data):
        """Update flow with nested nodes and connections"""
        nodes_data = validated_data.pop('nodes', None)
        connections_data = validated_data.pop('connections', None)
        
        # Update basic flow fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update nodes if provided
        if nodes_data is not None:
            # Clear existing nodes and connections
            instance.nodes.all().delete()
            instance.connections.all().delete()
            
            # Create new nodes and connections
            self._create_nodes(instance, nodes_data)
            if connections_data is not None:
                self._create_connections(instance, connections_data)
            
            # Update statistics
            instance.update_statistics()
            
            # Create history entry
            FlowHistory.objects.create(
                flow=instance,
                action='updated',
                user=self.context['request'].user,
                details=f"Flow updated with {len(nodes_data)} nodes and {len(connections_data or [])} connections"
            )
        
        return instance
    
    def _create_nodes(self, flow, nodes_data):
        """Create flow nodes with conditions"""
        node_objects = {}
        
        for node_data in nodes_data:
            # Extract position
            position = node_data.get('position', {})
            
            # Create node
            node = FlowNode.objects.create(
                flow=flow,
                node_id=node_data['id'],
                node_type=node_data['type'],
                name=node_data.get('properties', {}).get('name', f"{node_data['type'].title()} Node"),
                position_x=position.get('x', 0),
                position_y=position.get('y', 0),
                properties=node_data.get('properties', {})
            )
            
            node_objects[node_data['id']] = node
            
            # Create conditions for condition nodes
            if node_data['type'] == 'condition':
                self._create_node_conditions(node, node_data.get('properties', {}))
        
        return node_objects
    
    def _create_connections(self, flow, connections_data):
        """Create flow connections"""
        # Get all nodes for this flow
        nodes = {node.node_id: node for node in flow.nodes.all()}
        
        for conn_data in connections_data:
            start_node = nodes.get(conn_data['startNodeId'])
            end_node = nodes.get(conn_data['endNodeId'])
            
            if start_node and end_node:
                FlowConnection.objects.create(
                    flow=flow,
                    connection_id=conn_data['id'],
                    start_node=start_node,
                    end_node=end_node,
                    connection_type=conn_data.get('type', 'output')
                )
    
    def _create_node_conditions(self, node, properties):
        """Create conditions and groups for condition nodes"""
        conditions = properties.get('conditions', [])
        groups = properties.get('groups', [])
        
        # Create condition groups
        for group_data in groups:
            FlowConditionGroup.objects.create(
                node=node,
                group_id=group_data['id'],
                logic_operator=group_data.get('logic', 'AND'),
                parent_group=group_data.get('parentGroup')
            )
        
        # Create conditions
        for condition_data in conditions:
            FlowCondition.objects.create(
                node=node,
                condition_id=condition_data['id'],
                field=condition_data['field'],
                operator=condition_data['operator'],
                value=condition_data.get('value', ''),
                group_id=condition_data['group']
            )


class FlowExecutionStepSerializer(serializers.ModelSerializer):
    node = FlowNodeSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    approved_by = UserSerializer(read_only=True)
    
    class Meta:
        model = FlowExecutionStep
        fields = [
            'id', 'node', 'step_order', 'status', 'started_at', 'completed_at',
            'input_data', 'output_data', 'error_message', 'assigned_to', 
            'approved_by', 'approved_at'
        ]


class FlowExecutionSerializer(serializers.ModelSerializer):
    flow = FlowListSerializer(read_only=True)
    steps = FlowExecutionStepSerializer(many=True, read_only=True)
    current_node = FlowNodeSerializer(read_only=True)
    mpr_id = serializers.IntegerField(source='mpr.id', read_only=True)
    
    class Meta:
        model = FlowExecution
        fields = [
            'id', 'flow', 'mpr_id', 'current_node', 'status', 'started_at',
            'completed_at', 'error_message', 'execution_context', 'steps'
        ]


class FlowActivateSerializer(serializers.Serializer):
    """Serializer for activating a flow"""
    confirm = serializers.BooleanField(default=False)
    
    def validate_confirm(self, value):
        if not value:
            raise serializers.ValidationError("You must confirm flow activation")
        return value