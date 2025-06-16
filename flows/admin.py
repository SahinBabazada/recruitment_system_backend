# flows/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Flow, FlowNode, FlowConnection, FlowCondition, FlowConditionGroup,
    FlowHistory, FlowExecution, FlowExecutionStep
)


class FlowNodeInline(admin.TabularInline):
    model = FlowNode
    extra = 0
    fields = ['node_id', 'node_type', 'name', 'position_x', 'position_y']
    readonly_fields = ['node_id']


class FlowConnectionInline(admin.TabularInline):
    model = FlowConnection
    extra = 0
    fields = ['connection_id', 'start_node', 'end_node', 'connection_type']
    readonly_fields = ['connection_id']


class FlowHistoryInline(admin.TabularInline):
    model = FlowHistory
    extra = 0
    fields = ['action', 'user', 'timestamp', 'details']
    readonly_fields = ['action', 'user', 'timestamp', 'details']
    can_delete = False


@admin.register(Flow)
class FlowAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'version', 'status_badge', 'node_count', 'connection_count',
        'created_by', 'created_at', 'activated_at'
    ]
    list_filter = ['status', 'created_at', 'activated_at']
    search_fields = ['name', 'description']
    readonly_fields = [
        'version', 'node_count', 'connection_count', 'created_at', 
        'updated_at', 'activated_at'
    ]
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'description', 'status']
        }),
        ('Metadata', {
            'fields': [
                'version', 'created_by', 'activated_by', 'node_count', 
                'connection_count'
            ]
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at', 'activated_at'],
            'classes': ['collapse']
        })
    ]
    
    inlines = [FlowNodeInline, FlowConnectionInline, FlowHistoryInline]
    
    def status_badge(self, obj):
        colors = {
            'draft': '#ffc107',
            'active': '#28a745',
            'archived': '#6c757d'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 12px; font-size: 12px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'created_by', 'activated_by'
        )


class FlowConditionInline(admin.TabularInline):
    model = FlowCondition
    extra = 0
    fields = ['condition_id', 'field', 'operator', 'value', 'group_id']


class FlowConditionGroupInline(admin.TabularInline):
    model = FlowConditionGroup
    extra = 0
    fields = ['group_id', 'logic_operator', 'parent_group']


@admin.register(FlowNode)
class FlowNodeAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'flow', 'node_type', 'node_id', 'position_display', 'created_at'
    ]
    list_filter = ['node_type', 'flow', 'created_at']
    search_fields = ['name', 'node_id', 'flow__name']
    readonly_fields = ['node_id', 'created_at', 'updated_at']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['flow', 'node_id', 'node_type', 'name']
        }),
        ('Position', {
            'fields': ['position_x', 'position_y']
        }),
        ('Properties', {
            'fields': ['properties']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    inlines = [FlowConditionInline, FlowConditionGroupInline]
    
    def position_display(self, obj):
        return f"({obj.position_x}, {obj.position_y})"
    position_display.short_description = 'Position'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('flow')


@admin.register(FlowConnection)
class FlowConnectionAdmin(admin.ModelAdmin):
    list_display = [
        'connection_id', 'flow', 'start_node', 'end_node', 
        'connection_type', 'created_at'
    ]
    list_filter = ['connection_type', 'flow', 'created_at']
    search_fields = ['connection_id', 'flow__name']
    readonly_fields = ['connection_id', 'created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'flow', 'start_node', 'end_node'
        )


@admin.register(FlowHistory)
class FlowHistoryAdmin(admin.ModelAdmin):
    list_display = ['flow', 'action', 'user', 'timestamp', 'details_preview']
    list_filter = ['action', 'timestamp']
    search_fields = ['flow__name', 'user__username', 'details']
    readonly_fields = ['flow', 'action', 'user', 'timestamp', 'details', 'previous_state']
    
    def details_preview(self, obj):
        return obj.details[:50] + '...' if len(obj.details) > 50 else obj.details
    details_preview.short_description = 'Details'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('flow', 'user')


class FlowExecutionStepInline(admin.TabularInline):
    model = FlowExecutionStep
    extra = 0
    fields = [
        'step_order', 'node', 'status', 'assigned_to', 'approved_by', 
        'started_at', 'completed_at'
    ]
    readonly_fields = [
        'step_order', 'node', 'started_at', 'completed_at'
    ]


@admin.register(FlowExecution)
class FlowExecutionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'flow', 'mpr_link', 'status_badge', 'current_node', 
        'started_at', 'completed_at'
    ]
    list_filter = ['status', 'started_at', 'completed_at']
    search_fields = ['flow__name', 'mpr__position_title']
    readonly_fields = [
        'flow', 'mpr', 'started_at', 'completed_at', 'execution_context'
    ]
    
    fieldsets = [
        ('Execution Information', {
            'fields': ['flow', 'mpr', 'current_node', 'status']
        }),
        ('Timing', {
            'fields': ['started_at', 'completed_at']
        }),
        ('Error Information', {
            'fields': ['error_message'],
            'classes': ['collapse']
        }),
        ('Context Data', {
            'fields': ['execution_context'],
            'classes': ['collapse']
        })
    ]
    
    inlines = [FlowExecutionStepInline]
    
    def mpr_link(self, obj):
        url = reverse('admin:mpr_mpr_change', args=[obj.mpr.id])
        return format_html('<a href="{}">{}</a>', url, obj.mpr)
    mpr_link.short_description = 'MPR'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'in_progress': '#17a2b8',
            'completed': '#28a745',
            'failed': '#dc3545',
            'cancelled': '#6c757d'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 12px; font-size: 12px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'flow', 'mpr', 'current_node'
        )


@admin.register(FlowExecutionStep)
class FlowExecutionStepAdmin(admin.ModelAdmin):
    list_display = [
        'execution', 'step_order', 'node', 'status_badge', 
        'assigned_to', 'approved_by', 'started_at', 'completed_at'
    ]
    list_filter = ['status', 'started_at', 'completed_at']
    search_fields = ['execution__flow__name', 'node__name']
    readonly_fields = [
        'execution', 'node', 'step_order', 'started_at', 'completed_at',
        'input_data', 'output_data'
    ]
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'in_progress': '#17a2b8',
            'completed': '#28a745',
            'skipped': '#6c757d',
            'failed': '#dc3545'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 12px; font-size: 12px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'execution__flow', 'node', 'assigned_to', 'approved_by'
        )