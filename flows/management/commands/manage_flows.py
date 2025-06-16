# flows/management/commands/manage_flows.py
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from flows.models import Flow, FlowExecution, FlowExecutionStep
from flows.utils import FlowExecutor
import json

User = get_user_model()


class Command(BaseCommand):
    help = 'Manage flows - list, activate, deactivate, test, and cleanup'

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='action', help='Available actions')

        # List flows
        list_parser = subparsers.add_parser('list', help='List all flows')
        list_parser.add_argument(
            '--status',
            choices=['active', 'draft', 'archived'],
            help='Filter by status'
        )
        list_parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed information'
        )

        # Activate flow
        activate_parser = subparsers.add_parser('activate', help='Activate a flow')
        activate_parser.add_argument('flow_id', type=int, help='Flow ID to activate')
        activate_parser.add_argument(
            '--user',
            type=str,
            help='Username of the user activating the flow'
        )

        # Deactivate flow (archive)
        deactivate_parser = subparsers.add_parser('deactivate', help='Deactivate (archive) the active flow')
        deactivate_parser.add_argument(
            '--user',
            type=str,
            help='Username of the user deactivating the flow'
        )

        # Show flow details
        show_parser = subparsers.add_parser('show', help='Show detailed flow information')
        show_parser.add_argument('flow_id', type=int, help='Flow ID to show')

        # Test flow
        test_parser = subparsers.add_parser('test', help='Test flow execution (dry run)')
        test_parser.add_argument('flow_id', type=int, help='Flow ID to test')
        test_parser.add_argument(
            '--mpr-data',
            type=str,
            help='JSON string with MPR data for testing'
        )

        # Statistics
        stats_parser = subparsers.add_parser('stats', help='Show flow statistics')

        # Cleanup
        cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup old flow executions')
        cleanup_parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete executions older than N days (default: 30)'
        )
        cleanup_parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'list':
            self.list_flows(options)
        elif action == 'activate':
            self.activate_flow(options)
        elif action == 'deactivate':
            self.deactivate_flow(options)
        elif action == 'show':
            self.show_flow(options)
        elif action == 'test':
            self.test_flow(options)
        elif action == 'stats':
            self.show_statistics()
        elif action == 'cleanup':
            self.cleanup_executions(options)
        else:
            self.print_help('manage_flows', '')

    def list_flows(self, options):
        """List all flows with optional filtering"""
        queryset = Flow.objects.all()
        
        if options['status']:
            queryset = queryset.filter(status=options['status'])
        
        flows = queryset.order_by('-version', '-created_at')
        
        if not flows:
            self.stdout.write(self.style.WARNING('No flows found.'))
            return
        
        self.stdout.write(f"\n{'='*80}")
        self.stdout.write(self.style.HTTP_INFO('FLOWS LIST'))
        self.stdout.write(f"{'='*80}")
        
        for flow in flows:
            status_style = {
                'active': self.style.SUCCESS,
                'draft': self.style.WARNING,
                'archived': self.style.ERROR
            }.get(flow.status, self.style.HTTP_INFO)
            
            self.stdout.write(f"\n🔹 ID: {flow.id}")
            self.stdout.write(f"   Name: {flow.name}")
            self.stdout.write(f"   Version: {flow.version}")
            self.stdout.write(f"   Status: {status_style(flow.status.upper())}")
            self.stdout.write(f"   Nodes: {flow.node_count}, Connections: {flow.connection_count}")
            self.stdout.write(f"   Created: {flow.created_at.strftime('%Y-%m-%d %H:%M')} by {flow.created_by.username}")
            
            if flow.status == 'active':
                self.stdout.write(f"   Activated: {flow.activated_at.strftime('%Y-%m-%d %H:%M')} by {flow.activated_by.username}")
            
            if options['detailed']:
                self.stdout.write(f"   Description: {flow.description}")
                self.stdout.write(f"   Updated: {flow.updated_at.strftime('%Y-%m-%d %H:%M')}")
                
                # Show node types
                nodes = flow.nodes.all()
                if nodes:
                    node_types = {}
                    for node in nodes:
                        node_types[node.node_type] = node_types.get(node.node_type, 0) + 1
                    
                    node_summary = ", ".join([f"{count} {node_type}" for node_type, count in node_types.items()])
                    self.stdout.write(f"   Node Types: {node_summary}")
        
        self.stdout.write(f"\n{'='*80}")

    def activate_flow(self, options):
        """Activate a specific flow"""
        try:
            flow = Flow.objects.get(id=options['flow_id'])
        except Flow.DoesNotExist:
            raise CommandError(f"Flow with ID {options['flow_id']} not found")
        
        if flow.status == 'active':
            self.stdout.write(self.style.WARNING(f"Flow '{flow.name}' is already active"))
            return
        
        user = self.get_user(options.get('user'))
        
        # Check if there's currently an active flow
        current_active = Flow.get_active_flow()
        
        with transaction.atomic():
            flow.activate(user)
            
            self.stdout.write(
                self.style.SUCCESS(f"✅ Flow '{flow.name}' v{flow.version} activated successfully!")
            )
            
            if current_active:
                self.stdout.write(
                    self.style.WARNING(f"⚠️  Previous active flow '{current_active.name}' v{current_active.version} has been archived")
                )

    def deactivate_flow(self, options):
        """Deactivate the currently active flow"""
        active_flow = Flow.get_active_flow()
        
        if not active_flow:
            self.stdout.write(self.style.WARNING("No active flow found"))
            return
        
        user = self.get_user(options.get('user'))
        
        with transaction.atomic():
            active_flow.status = 'archived'
            active_flow.save()
            
            # Create history entry
            from flows.models import FlowHistory
            FlowHistory.objects.create(
                flow=active_flow,
                action='archived',
                user=user,
                details=f"Flow v{active_flow.version} deactivated via management command"
            )
        
        self.stdout.write(
            self.style.SUCCESS(f"✅ Flow '{active_flow.name}' v{active_flow.version} has been deactivated")
        )

    def show_flow(self, options):
        """Show detailed information about a specific flow"""
        try:
            flow = Flow.objects.get(id=options['flow_id'])
        except Flow.DoesNotExist:
            raise CommandError(f"Flow with ID {options['flow_id']} not found")
        
        self.stdout.write(f"\n{'='*80}")
        self.stdout.write(self.style.HTTP_INFO(f"FLOW DETAILS - {flow.name}"))
        self.stdout.write(f"{'='*80}")
        
        # Basic info
        status_style = {
            'active': self.style.SUCCESS,
            'draft': self.style.WARNING,
            'archived': self.style.ERROR
        }.get(flow.status, self.style.HTTP_INFO)
        
        self.stdout.write(f"ID: {flow.id}")
        self.stdout.write(f"Name: {flow.name}")
        self.stdout.write(f"Version: {flow.version}")
        self.stdout.write(f"Status: {status_style(flow.status.upper())}")
        self.stdout.write(f"Description: {flow.description}")
        self.stdout.write(f"Created: {flow.created_at} by {flow.created_by.username}")
        self.stdout.write(f"Updated: {flow.updated_at}")
        
        if flow.status == 'active':
            self.stdout.write(f"Activated: {flow.activated_at} by {flow.activated_by.username}")
        
        # Statistics
        self.stdout.write(f"\nStatistics:")
        self.stdout.write(f"  Nodes: {flow.node_count}")
        self.stdout.write(f"  Connections: {flow.connection_count}")
        self.stdout.write(f"  Executions: {flow.executions.count()}")
        
        # Nodes
        nodes = flow.nodes.all().order_by('created_at')
        if nodes:
            self.stdout.write(f"\nNodes ({len(nodes)}):")
            for i, node in enumerate(nodes, 1):
                self.stdout.write(f"  {i:2d}. {node.name} ({node.node_type})")
                if node.node_type == 'condition':
                    conditions_count = node.conditions.count()
                    if conditions_count:
                        self.stdout.write(f"      └─ {conditions_count} conditions")
        
        # Connections
        connections = flow.connections.all()
        if connections:
            self.stdout.write(f"\nConnections ({len(connections)}):")
            for i, conn in enumerate(connections, 1):
                self.stdout.write(f"  {i:2d}. {conn.start_node.name} → {conn.end_node.name} ({conn.connection_type})")
        
        # Recent executions
        recent_executions = flow.executions.order_by('-started_at')[:5]
        if recent_executions:
            self.stdout.write(f"\nRecent Executions (latest 5):")
            for execution in recent_executions:
                status_symbol = {
                    'pending': '⏳',
                    'in_progress': '🔄',
                    'completed': '✅',
                    'failed': '❌',
                    'cancelled': '⚠️'
                }.get(execution.status, '❓')
                
                self.stdout.write(f"  {status_symbol} {execution.started_at.strftime('%Y-%m-%d %H:%M')} - {execution.status}")
        
        self.stdout.write(f"{'='*80}")

    def test_flow(self, options):
        """Test flow execution with sample data"""
        try:
            flow = Flow.objects.get(id=options['flow_id'])
        except Flow.DoesNotExist:
            raise CommandError(f"Flow with ID {options['flow_id']} not found")
        
        # Parse MPR data
        mpr_data = {}
        if options.get('mpr_data'):
            try:
                mpr_data = json.loads(options['mpr_data'])
            except json.JSONDecodeError:
                raise CommandError("Invalid JSON format for MPR data")
        else:
            # Use default test data
            mpr_data = {
                'priority': 'normal',
                'department': 'Engineering',
                'budget_amount': 75000,
                'employment_type': 'permanent',
                'location': 'Remote',
                'hiring_reason': 'growth',
                'position_title': 'Senior Software Engineer'
            }
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.HTTP_INFO(f"TESTING FLOW: {flow.name}"))
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"Test Data: {json.dumps(mpr_data, indent=2)}")
        self.stdout.write(f"{'='*60}")
        
        # Simulate flow execution
        self.simulate_flow_execution(flow, mpr_data)

    def simulate_flow_execution(self, flow, mpr_data):
        """Simulate flow execution without creating actual records"""
        # Find start node
        start_node = flow.nodes.filter(node_type='start').first()
        if not start_node:
            self.stdout.write(self.style.ERROR("❌ No start node found in flow"))
            return
        
        current_node = start_node
        step_number = 1
        visited_nodes = set()
        
        self.stdout.write(f"\n🏁 Starting flow execution simulation...")
        
        while current_node and current_node.id not in visited_nodes:
            visited_nodes.add(current_node.id)
            
            # Process current node
            self.stdout.write(f"\n📍 Step {step_number}: {current_node.name} ({current_node.node_type})")
            
            if current_node.node_type == 'start':
                self.stdout.write("   ✅ Flow started")
                
            elif current_node.node_type == 'condition':
                result = self.evaluate_test_conditions(current_node, mpr_data)
                self.stdout.write(f"   🔍 Condition evaluated: {result}")
                
            elif current_node.node_type == 'approval':
                approver_type = current_node.properties.get('approverType', 'unknown')
                timeout_days = current_node.properties.get('timeoutDays', 5)
                self.stdout.write(f"   ⏳ Requires approval from: {approver_type}")
                self.stdout.write(f"   📅 Timeout: {timeout_days} days")
                
            elif current_node.node_type == 'notification':
                recipients = current_node.properties.get('recipients', 'unknown')
                subject = current_node.properties.get('subject', 'No subject')
                self.stdout.write(f"   📧 Notification sent to: {recipients}")
                self.stdout.write(f"   📝 Subject: {subject}")
                
            elif current_node.node_type == 'end':
                final_status = current_node.properties.get('finalStatus', 'completed')
                self.stdout.write(f"   🎯 Flow completed with status: {final_status}")
                break
            
            # Find next node
            next_node = self.get_next_test_node(current_node, mpr_data)
            if next_node:
                self.stdout.write(f"   ➡️  Next: {next_node.name}")
                current_node = next_node
                step_number += 1
            else:
                self.stdout.write("   ⚠️  No next node found - flow ends here")
                break
            
            # Safety check to prevent infinite loops
            if step_number > 20:
                self.stdout.write(self.style.ERROR("   ❌ Flow simulation stopped - too many steps (possible loop)"))
                break
        
        self.stdout.write(f"\n✅ Flow simulation completed in {step_number} steps")

    def evaluate_test_conditions(self, condition_node, mpr_data):
        """Evaluate conditions for testing"""
        conditions = condition_node.conditions.all()
        if not conditions:
            return False
        
        # Simple evaluation - just check first condition for demo
        first_condition = conditions.first()
        field_value = mpr_data.get(first_condition.field)
        condition_value = first_condition.value
        
        if first_condition.operator == 'equals':
            return str(field_value) == str(condition_value)
        elif first_condition.operator == 'greater_than':
            try:
                return float(field_value) > float(condition_value)
            except (ValueError, TypeError):
                return False
        # Add more operators as needed
        
        return False

    def get_next_test_node(self, current_node, mpr_data):
        """Get next node for testing"""
        connections = current_node.outgoing_connections.all()
        
        if not connections:
            return None
        
        if current_node.node_type == 'condition':
            # Evaluate condition and choose path
            result = self.evaluate_test_conditions(current_node, mpr_data)
            connection_type = 'true' if result else 'false'
            connection = connections.filter(connection_type=connection_type).first()
        else:
            # Take first available connection
            connection = connections.first()
        
        return connection.end_node if connection else None

    def show_statistics(self):
        """Show comprehensive flow statistics"""
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.HTTP_INFO('FLOW STATISTICS'))
        self.stdout.write(f"{'='*60}")
        
        # Flow counts
        total_flows = Flow.objects.count()
        active_flows = Flow.objects.filter(status='active').count()
        draft_flows = Flow.objects.filter(status='draft').count()
        archived_flows = Flow.objects.filter(status='archived').count()
        
        self.stdout.write(f"📊 Flow Counts:")
        self.stdout.write(f"   Total: {total_flows}")
        self.stdout.write(f"   Active: {self.style.SUCCESS(str(active_flows))}")
        self.stdout.write(f"   Draft: {self.style.WARNING(str(draft_flows))}")
        self.stdout.write(f"   Archived: {archived_flows}")
        
        # Execution statistics
        total_executions = FlowExecution.objects.count()
        pending_executions = FlowExecution.objects.filter(status='pending').count()
        in_progress_executions = FlowExecution.objects.filter(status='in_progress').count()
        completed_executions = FlowExecution.objects.filter(status='completed').count()
        failed_executions = FlowExecution.objects.filter(status='failed').count()
        
        self.stdout.write(f"\n🔄 Execution Statistics:")
        self.stdout.write(f"   Total Executions: {total_executions}")
        self.stdout.write(f"   Pending: {self.style.WARNING(str(pending_executions))}")
        self.stdout.write(f"   In Progress: {self.style.HTTP_INFO(str(in_progress_executions))}")
        self.stdout.write(f"   Completed: {self.style.SUCCESS(str(completed_executions))}")
        self.stdout.write(f"   Failed: {self.style.ERROR(str(failed_executions))}")
        
        # Active flow info
        active_flow = Flow.get_active_flow()
        if active_flow:
            self.stdout.write(f"\n🎯 Currently Active Flow:")
            self.stdout.write(f"   Name: {active_flow.name}")
            self.stdout.write(f"   Version: {active_flow.version}")
            self.stdout.write(f"   Activated: {active_flow.activated_at}")
            self.stdout.write(f"   Executions: {active_flow.executions.count()}")
        else:
            self.stdout.write(f"\n⚠️  No active flow configured")
        
        # Pending approvals
        pending_steps = FlowExecutionStep.objects.filter(status='in_progress').count()
        if pending_steps > 0:
            self.stdout.write(f"\n⏳ Pending Approvals: {self.style.WARNING(str(pending_steps))}")
        
        self.stdout.write(f"{'='*60}")

    def cleanup_executions(self, options):
        """Cleanup old flow executions"""
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        cutoff_date = timezone.now() - timedelta(days=options['days'])
        old_executions = FlowExecution.objects.filter(
            started_at__lt=cutoff_date,
            status__in=['completed', 'failed', 'cancelled']
        )
        
        count = old_executions.count()
        
        if count == 0:
            self.stdout.write(self.style.WARNING(f"No executions found older than {options['days']} days"))
            return
        
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.HTTP_INFO('CLEANUP SUMMARY'))
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"Executions to delete: {count}")
        self.stdout.write(f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING("\n🔍 DRY RUN - No actual deletion performed"))
            
            # Show what would be deleted
            for execution in old_executions[:10]:  # Show first 10
                self.stdout.write(f"   - Execution {execution.id}: {execution.started_at} ({execution.status})")
            
            if count > 10:
                self.stdout.write(f"   ... and {count - 10} more")
        else:
            # Perform actual deletion
            deleted_count, _ = old_executions.delete()
            self.stdout.write(self.style.SUCCESS(f"\n✅ Deleted {deleted_count} old flow executions"))
        
        self.stdout.write(f"{'='*60}")

    def get_user(self, username):
        """Get user for operations"""
        if username:
            try:
                return User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(f"User '{username}' not found")
        
        # Default to first superuser
        superuser = User.objects.filter(is_superuser=True).first()
        if not superuser:
            raise CommandError("No superuser found. Please create a superuser first or specify --user")
        
        return superuser