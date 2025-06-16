# flows/signals.py
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import Flow, FlowNode, FlowConnection, FlowHistory


@receiver(post_save, sender=FlowNode)
def update_flow_stats_on_node_change(sender, instance, created, **kwargs):
    """Update flow statistics when nodes are added/updated"""
    if created:
        instance.flow.update_statistics()
        
        # Create history entry
        FlowHistory.objects.create(
            flow=instance.flow,
            action='node_added',
            user=instance.flow.created_by,  # Default to flow creator
            details=f"Node '{instance.name}' ({instance.node_type}) added"
        )


@receiver(post_save, sender=FlowConnection)
def update_flow_stats_on_connection_change(sender, instance, created, **kwargs):
    """Update flow statistics when connections are added/updated"""
    if created:
        instance.flow.update_statistics()
        
        # Create history entry
        FlowHistory.objects.create(
            flow=instance.flow,
            action='connection_added',
            user=instance.flow.created_by,  # Default to flow creator
            details=f"Connection from '{instance.start_node.name}' to '{instance.end_node.name}' added"
        )


@receiver(pre_delete, sender=FlowNode)
def track_node_deletion(sender, instance, **kwargs):
    """Track node deletion in history"""
    FlowHistory.objects.create(
        flow=instance.flow,
        action='node_deleted',
        user=instance.flow.created_by,  # Default to flow creator
        details=f"Node '{instance.name}' ({instance.node_type}) deleted",
        previous_state={
            'node_id': instance.node_id,
            'node_type': instance.node_type,
            'name': instance.name,
            'properties': instance.properties
        }
    )


@receiver(pre_delete, sender=FlowConnection)
def track_connection_deletion(sender, instance, **kwargs):
    """Track connection deletion in history"""
    FlowHistory.objects.create(
        flow=instance.flow,
        action='connection_deleted',
        user=instance.flow.created_by,  # Default to flow creator
        details=f"Connection from '{instance.start_node.name}' to '{instance.end_node.name}' deleted",
        previous_state={
            'connection_id': instance.connection_id,
            'connection_type': instance.connection_type,
            'start_node': instance.start_node.name,
            'end_node': instance.end_node.name
        }
    )