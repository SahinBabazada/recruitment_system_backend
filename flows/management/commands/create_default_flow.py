# flows/management/commands/create_default_flow.py
import json
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from flows.models import Flow, FlowNode, FlowConnection, FlowCondition, FlowConditionGroup, FlowHistory

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a default approval flow for MPRs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--name',
            type=str,
            default='Default MPR Approval Flow',
            help='Name for the default flow'
        )
        parser.add_argument(
            '--activate',
            action='store_true',
            help='Activate the flow after creation'
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Username of the user to set as creator (defaults to first superuser)'
        )
        parser.add_argument(
            '--template',
            type=str,
            choices=['simple', 'conditional', 'comprehensive'],
            default='simple',
            help='Template type to use for the default flow'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if a default flow already exists'
        )

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                # Get or create user
                user = self.get_user(options['user'])
                
                # Check if default flow already exists
                if not options['force'] and Flow.objects.filter(name=options['name']).exists():
                    raise CommandError(f"Flow with name '{options['name']}' already exists. Use --force to override.")
                
                # Create flow based on template
                flow = self.create_flow_from_template(
                    options['template'], 
                    options['name'], 
                    user
                )
                
                # Activate if requested
                if options['activate']:
                    flow.activate(user)
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Flow "{flow.name}" created and activated successfully!')
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Flow "{flow.name}" created successfully!')
                    )
                
                # Print flow details
                self.print_flow_summary(flow)
                
        except Exception as e:
            raise CommandError(f'Failed to create default flow: {str(e)}')

    def get_user(self, username):
        """Get user for flow creation"""
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

    def create_flow_from_template(self, template_type, name, user):
        """Create flow based on template type"""
        if template_type == 'simple':
            return self.create_simple_flow(name, user)
        elif template_type == 'conditional':
            return self.create_conditional_flow(name, user)
        elif template_type == 'comprehensive':
            return self.create_comprehensive_flow(name, user)
        else:
            raise CommandError(f"Unknown template type: {template_type}")

    def create_simple_flow(self, name, user):
        """Create a simple approval flow: Start → Manager → Budget Holder → End"""
        self.stdout.write("Creating simple approval flow...")
        
        # Create flow
        flow = Flow.objects.create(
            name=name,
            description="Simple approval flow: Manager → Budget Holder",
            status='draft',
            created_by=user
        )
        
        # Create nodes
        nodes = [
            {
                'node_id': 'start_1',
                'node_type': 'start',
                'name': 'Flow Start',
                'position_x': 100,
                'position_y': 200,
                'properties': {
                    'name': 'Flow Start',
                    'description': 'MPR submission begins here'
                }
            },
            {
                'node_id': 'approval_1',
                'node_type': 'approval',
                'name': 'Manager Approval',
                'position_x': 350,
                'position_y': 200,
                'properties': {
                    'name': 'Manager Approval',
                    'approverType': 'manager',
                    'timeoutDays': 5,
                    'reminderDays': 3,
                    'escalationTo': 'manager'
                }
            },
            {
                'node_id': 'approval_2',
                'node_type': 'approval',
                'name': 'Budget Approval',
                'position_x': 600,
                'position_y': 200,
                'properties': {
                    'name': 'Budget Approval',
                    'approverType': 'budget_holder',
                    'timeoutDays': 7,
                    'reminderDays': 5,
                    'escalationTo': 'budget_sponsor'
                }
            },
            {
                'node_id': 'end_1',
                'node_type': 'end',
                'name': 'Flow End',
                'position_x': 850,
                'position_y': 200,
                'properties': {
                    'name': 'Flow End',
                    'finalStatus': 'approved',
                    'sendFinalNotification': True,
                    'createJobPosting': True
                }
            }
        ]
        
        # Create connections
        connections = [
            {
                'connection_id': 'conn_1',
                'start_node_id': 'start_1',
                'end_node_id': 'approval_1',
                'connection_type': 'output'
            },
            {
                'connection_id': 'conn_2',
                'start_node_id': 'approval_1',
                'end_node_id': 'approval_2',
                'connection_type': 'output'
            },
            {
                'connection_id': 'conn_3',
                'start_node_id': 'approval_2',
                'end_node_id': 'end_1',
                'connection_type': 'output'
            }
        ]
        
        self.create_flow_elements(flow, nodes, connections)
        return flow

    def create_conditional_flow(self, name, user):
        """Create a conditional flow with budget-based routing"""
        self.stdout.write("Creating conditional approval flow...")
        
        # Create flow
        flow = Flow.objects.create(
            name=name,
            description="Conditional approval flow based on budget amount and priority",
            status='draft',
            created_by=user
        )
        
        # Create nodes
        nodes = [
            {
                'node_id': 'start_1',
                'node_type': 'start',
                'name': 'Flow Start',
                'position_x': 100,
                'position_y': 250,
                'properties': {
                    'name': 'Flow Start',
                    'description': 'MPR submission begins here'
                }
            },
            {
                'node_id': 'condition_1',
                'node_type': 'condition',
                'name': 'Budget & Priority Check',
                'position_x': 300,
                'position_y': 250,
                'properties': {
                    'name': 'Budget & Priority Check',
                    'logicOperator': 'OR',
                    'conditions': [
                        {
                            'id': 1,
                            'field': 'budget_amount',
                            'operator': 'greater_than',
                            'value': '75000',
                            'group': 1
                        },
                        {
                            'id': 2,
                            'field': 'priority',
                            'operator': 'equals',
                            'value': 'urgent',
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
                'node_id': 'approval_1',
                'node_type': 'approval',
                'name': 'Executive Approval',
                'position_x': 200,
                'position_y': 150,
                'properties': {
                    'name': 'Executive Approval',
                    'approverType': 'budget_sponsor',
                    'timeoutDays': 3,
                    'reminderDays': 2,
                    'escalationTo': 'ceo'
                }
            },
            {
                'node_id': 'approval_2',
                'node_type': 'approval',
                'name': 'Manager Approval',
                'position_x': 200,
                'position_y': 350,
                'properties': {
                    'name': 'Manager Approval',
                    'approverType': 'manager',
                    'timeoutDays': 5,
                    'reminderDays': 3,
                    'escalationTo': 'budget_holder'
                }
            },
            {
                'node_id': 'notification_1',
                'node_type': 'notification',
                'name': 'Approval Notification',
                'position_x': 500,
                'position_y': 250,
                'properties': {
                    'name': 'Approval Notification',
                    'recipients': 'creator,manager,recruiter',
                    'subject': 'MPR Approved: {position}',
                    'message': 'The MPR for {position} has been approved and is ready for next steps.',
                    'priority': 'normal',
                    'delivery': 'email'
                }
            },
            {
                'node_id': 'end_1',
                'node_type': 'end',
                'name': 'Flow End',
                'position_x': 700,
                'position_y': 250,
                'properties': {
                    'name': 'Flow End',
                    'finalStatus': 'approved',
                    'sendFinalNotification': True,
                    'createJobPosting': True
                }
            }
        ]
        
        # Create connections
        connections = [
            {
                'connection_id': 'conn_1',
                'start_node_id': 'start_1',
                'end_node_id': 'condition_1',
                'connection_type': 'output'
            },
            {
                'connection_id': 'conn_2',
                'start_node_id': 'condition_1',
                'end_node_id': 'approval_1',
                'connection_type': 'true'
            },
            {
                'connection_id': 'conn_3',
                'start_node_id': 'condition_1',
                'end_node_id': 'approval_2',
                'connection_type': 'false'
            },
            {
                'connection_id': 'conn_4',
                'start_node_id': 'approval_1',
                'end_node_id': 'notification_1',
                'connection_type': 'output'
            },
            {
                'connection_id': 'conn_5',
                'start_node_id': 'approval_2',
                'end_node_id': 'notification_1',
                'connection_type': 'output'
            },
            {
                'connection_id': 'conn_6',
                'start_node_id': 'notification_1',
                'end_node_id': 'end_1',
                'connection_type': 'output'
            }
        ]
        
        self.create_flow_elements(flow, nodes, connections)
        self.create_flow_conditions(flow)
        return flow

    def create_comprehensive_flow(self, name, user):
        """Create a comprehensive flow with multiple approval stages and conditions"""
        self.stdout.write("Creating comprehensive approval flow...")
        
        # Create flow
        flow = Flow.objects.create(
            name=name,
            description="Comprehensive multi-stage approval flow with conditions and notifications",
            status='draft',
            created_by=user
        )
        
        # Create nodes
        nodes = [
            {
                'node_id': 'start_1',
                'node_type': 'start',
                'name': 'MPR Submission',
                'position_x': 50,
                'position_y': 300,
                'properties': {
                    'name': 'MPR Submission',
                    'description': 'New MPR request submitted for approval'
                }
            },
            {
                'node_id': 'notification_1',
                'node_type': 'notification',
                'name': 'Submission Notification',
                'position_x': 200,
                'position_y': 300,
                'properties': {
                    'name': 'Submission Notification',
                    'recipients': 'creator,manager',
                    'subject': 'MPR Submitted: {position}',
                    'message': 'A new MPR for {position} has been submitted and is now in the approval process.',
                    'priority': 'normal',
                    'delivery': 'email'
                }
            },
            {
                'node_id': 'condition_1',
                'node_type': 'condition',
                'name': 'Initial Routing',
                'position_x': 350,
                'position_y': 300,
                'properties': {
                    'name': 'Initial Routing',
                    'logicOperator': 'OR',
                    'conditions': [
                        {
                            'id': 1,
                            'field': 'employment_type',
                            'operator': 'equals',
                            'value': 'contractor',
                            'group': 1
                        },
                        {
                            'id': 2,
                            'field': 'budget_amount',
                            'operator': 'less_than',
                            'value': '25000',
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
                'node_id': 'approval_1',
                'node_type': 'approval',
                'name': 'Quick Approval',
                'position_x': 500,
                'position_y': 200,
                'properties': {
                    'name': 'Quick Approval',
                    'approverType': 'manager',
                    'timeoutDays': 3,
                    'reminderDays': 2,
                    'escalationTo': 'budget_holder'
                }
            },
            {
                'node_id': 'approval_2',
                'node_type': 'approval',
                'name': 'Manager Approval',
                'position_x': 500,
                'position_y': 400,
                'properties': {
                    'name': 'Manager Approval',
                    'approverType': 'manager',
                    'timeoutDays': 5,
                    'reminderDays': 3,
                    'escalationTo': 'budget_holder'
                }
            },
            {
                'node_id': 'condition_2',
                'node_type': 'condition',
                'name': 'Budget Check',
                'position_x': 650,
                'position_y': 400,
                'properties': {
                    'name': 'Budget Check',
                    'logicOperator': 'AND',
                    'conditions': [
                        {
                            'id': 3,
                            'field': 'budget_amount',
                            'operator': 'greater_than',
                            'value': '50000',
                            'group': 3
                        }
                    ],
                    'groups': [
                        {'id': 3, 'logic': 'AND', 'parentGroup': None}
                    ]
                }
            },
            {
                'node_id': 'approval_3',
                'node_type': 'approval',
                'name': 'Budget Holder Approval',
                'position_x': 800,
                'position_y': 350,
                'properties': {
                    'name': 'Budget Holder Approval',
                    'approverType': 'budget_holder',
                    'timeoutDays': 7,
                    'reminderDays': 5,
                    'escalationTo': 'budget_sponsor'
                }
            },
            {
                'node_id': 'approval_4',
                'node_type': 'approval',
                'name': 'Executive Approval',
                'position_x': 800,
                'position_y': 250,
                'properties': {
                    'name': 'Executive Approval',
                    'approverType': 'budget_sponsor',
                    'timeoutDays': 5,
                    'reminderDays': 3,
                    'escalationTo': 'ceo'
                }
            },
            {
                'node_id': 'notification_2',
                'node_type': 'notification',
                'name': 'Final Notification',
                'position_x': 950,
                'position_y': 300,
                'properties': {
                    'name': 'Final Notification',
                    'recipients': 'creator,manager,recruiter,hr_director',
                    'subject': 'MPR Fully Approved: {position}',
                    'message': 'The MPR for {position} has completed all approval stages and is ready for job posting.',
                    'priority': 'high',
                    'delivery': 'both'
                }
            },
            {
                'node_id': 'end_1',
                'node_type': 'end',
                'name': 'Flow Complete',
                'position_x': 1100,
                'position_y': 300,
                'properties': {
                    'name': 'Flow Complete',
                    'finalStatus': 'approved',
                    'sendFinalNotification': True,
                    'archiveRequest': False,
                    'createJobPosting': True
                }
            }
        ]
        
        # Create connections
        connections = [
            {'connection_id': 'conn_1', 'start_node_id': 'start_1', 'end_node_id': 'notification_1', 'connection_type': 'output'},
            {'connection_id': 'conn_2', 'start_node_id': 'notification_1', 'end_node_id': 'condition_1', 'connection_type': 'output'},
            {'connection_id': 'conn_3', 'start_node_id': 'condition_1', 'end_node_id': 'approval_1', 'connection_type': 'true'},
            {'connection_id': 'conn_4', 'start_node_id': 'condition_1', 'end_node_id': 'approval_2', 'connection_type': 'false'},
            {'connection_id': 'conn_5', 'start_node_id': 'approval_1', 'end_node_id': 'notification_2', 'connection_type': 'output'},
            {'connection_id': 'conn_6', 'start_node_id': 'approval_2', 'end_node_id': 'condition_2', 'connection_type': 'output'},
            {'connection_id': 'conn_7', 'start_node_id': 'condition_2', 'end_node_id': 'approval_4', 'connection_type': 'true'},
            {'connection_id': 'conn_8', 'start_node_id': 'condition_2', 'end_node_id': 'approval_3', 'connection_type': 'false'},
            {'connection_id': 'conn_9', 'start_node_id': 'approval_3', 'end_node_id': 'notification_2', 'connection_type': 'output'},
            {'connection_id': 'conn_10', 'start_node_id': 'approval_4', 'end_node_id': 'notification_2', 'connection_type': 'output'},
            {'connection_id': 'conn_11', 'start_node_id': 'notification_2', 'end_node_id': 'end_1', 'connection_type': 'output'}
        ]
        
        self.create_flow_elements(flow, nodes, connections)
        self.create_flow_conditions(flow)
        return flow

    def create_flow_elements(self, flow, nodes_data, connections_data):
        """Create flow nodes and connections"""
        # Create nodes
        node_objects = {}
        for node_data in nodes_data:
            node = FlowNode.objects.create(
                flow=flow,
                **node_data
            )
            node_objects[node_data['node_id']] = node
        
        # Create connections
        for conn_data in connections_data:
            FlowConnection.objects.create(
                flow=flow,
                connection_id=conn_data['connection_id'],
                start_node=node_objects[conn_data['start_node_id']],
                end_node=node_objects[conn_data['end_node_id']],
                connection_type=conn_data['connection_type']
            )
        
        # Update flow statistics
        flow.update_statistics()

    def create_flow_conditions(self, flow):
        """Create conditions for condition nodes"""
        condition_nodes = flow.nodes.filter(node_type='condition')
        
        for node in condition_nodes:
            properties = node.properties
            
            # Create condition groups
            for group_data in properties.get('groups', []):
                FlowConditionGroup.objects.create(
                    node=node,
                    group_id=group_data['id'],
                    logic_operator=group_data.get('logic', 'AND'),
                    parent_group=group_data.get('parentGroup')
                )
            
            # Create conditions
            for condition_data in properties.get('conditions', []):
                FlowCondition.objects.create(
                    node=node,
                    condition_id=condition_data['id'],
                    field=condition_data['field'],
                    operator=condition_data['operator'],
                    value=condition_data.get('value', ''),
                    group_id=condition_data['group']
                )

    def print_flow_summary(self, flow):
        """Print a summary of the created flow"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.HTTP_INFO(f"FLOW SUMMARY"))
        self.stdout.write("="*60)
        self.stdout.write(f"Name: {flow.name}")
        self.stdout.write(f"Version: {flow.version}")
        self.stdout.write(f"Status: {flow.status}")
        self.stdout.write(f"Nodes: {flow.node_count}")
        self.stdout.write(f"Connections: {flow.connection_count}")
        self.stdout.write(f"Created by: {flow.created_by.username}")
        self.stdout.write(f"Created at: {flow.created_at}")
        
        if flow.status == 'active':
            self.stdout.write(f"Activated at: {flow.activated_at}")
            self.stdout.write(f"Activated by: {flow.activated_by.username}")
        
        # Print nodes
        self.stdout.write("\nNodes:")
        for node in flow.nodes.all():
            self.stdout.write(f"  • {node.name} ({node.node_type})")
        
        # Print connections
        self.stdout.write("\nConnections:")
        for conn in flow.connections.all():
            self.stdout.write(f"  • {conn.start_node.name} → {conn.end_node.name} ({conn.connection_type})")
        
        self.stdout.write("="*60)
        
        # Usage instructions
        self.stdout.write(self.style.WARNING("\n📋 NEXT STEPS:"))
        if flow.status == 'draft':
            self.stdout.write("1. Review the flow in the admin interface or frontend")
            self.stdout.write("2. Activate the flow when ready:")
            self.stdout.write(f"   python manage.py create_default_flow --name '{flow.name}' --activate --force")
        else:
            self.stdout.write("1. The flow is now active and ready to process MPRs")
            self.stdout.write("2. Test the flow with a sample MPR")
            self.stdout.write("3. Monitor flow executions in the admin interface")
        
        self.stdout.write("="*60)