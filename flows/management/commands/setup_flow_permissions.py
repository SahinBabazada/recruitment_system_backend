# flows/management/commands/setup_flow_permissions.py
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = 'Setup default permissions and roles for flow management'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-permissions',
            action='store_true',
            help='Create flow-related permissions'
        )
        parser.add_argument(
            '--assign-admin',
            type=str,
            help='Assign all flow permissions to specified user'
        )
        parser.add_argument(
            '--assign-manager',
            type=str,
            help='Assign manager-level flow permissions to specified user'
        )
        parser.add_argument(
            '--list-permissions',
            action='store_true',
            help='List all flow-related permissions'
        )

    def handle(self, *args, **options):
        if options['create_permissions']:
            self.create_flow_permissions()
        
        if options['list_permissions']:
            self.list_flow_permissions()
        
        if options['assign_admin']:
            self.assign_admin_permissions(options['assign_admin'])
        
        if options['assign_manager']:
            self.assign_manager_permissions(options['assign_manager'])
        
        if not any([
            options['create_permissions'],
            options['list_permissions'], 
            options['assign_admin'],
            options['assign_manager']
        ]):
            self.print_help('setup_flow_permissions', '')

    def create_flow_permissions(self):
        """Create flow-related permissions"""
        try:
            # Try to import permissions app
            from permissions.models import Permission
            
            flow_permissions = [
                {
                    'name': 'flow:view',
                    'description': 'View flows and flow details',
                    'module': 'flow',
                    'action': 'view'
                },
                {
                    'name': 'flow:create',
                    'description': 'Create new flows',
                    'module': 'flow',
                    'action': 'create'
                },
                {
                    'name': 'flow:edit',
                    'description': 'Edit existing flows',
                    'module': 'flow',
                    'action': 'edit'
                },
                {
                    'name': 'flow:delete',
                    'description': 'Delete flows',
                    'module': 'flow',
                    'action': 'delete'
                },
                {
                    'name': 'flow:activate',
                    'description': 'Activate and deactivate flows',
                    'module': 'flow',
                    'action': 'activate'
                },
                {
                    'name': 'flow:execute',
                    'description': 'Execute flows on MPRs',
                    'module': 'flow',
                    'action': 'execute'
                },
                {
                    'name': 'flow:approve',
                    'description': 'Approve flow execution steps',
                    'module': 'flow',
                    'action': 'approve'
                },
                {
                    'name': 'flow:approve_on_behalf',
                    'description': 'Approve flow steps on behalf of other users',
                    'module': 'flow',
                    'action': 'approve_on_behalf'
                },
                {
                    'name': 'flow:monitor',
                    'description': 'Monitor flow executions and statistics',
                    'module': 'flow',
                    'action': 'monitor'
                },
                {
                    'name': 'flow:manage_templates',
                    'description': 'Manage flow templates',
                    'module': 'flow',
                    'action': 'manage_templates'
                }
            ]
            
            created_count = 0
            updated_count = 0
            
            self.stdout.write("Creating flow permissions...")
            
            with transaction.atomic():
                for perm_data in flow_permissions:
                    permission, created = Permission.objects.get_or_create(
                        name=perm_data['name'],
                        defaults={
                            'description': perm_data['description'],
                            'module': perm_data['module'],
                            'action': perm_data['action']
                        }
                    )
                    
                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"✅ Created: {perm_data['name']}")
                        )
                    else:
                        # Update description if it changed
                        if permission.description != perm_data['description']:
                            permission.description = perm_data['description']
                            permission.save()
                            updated_count += 1
                            self.stdout.write(
                                self.style.WARNING(f"📝 Updated: {perm_data['name']}")
                            )
                        else:
                            self.stdout.write(f"   Exists: {perm_data['name']}")
            
            self.stdout.write(f"\n{'='*50}")
            self.stdout.write(self.style.SUCCESS(f"✅ Flow permissions setup complete!"))
            self.stdout.write(f"   Created: {created_count}")
            self.stdout.write(f"   Updated: {updated_count}")
            self.stdout.write(f"   Total: {len(flow_permissions)}")
            self.stdout.write(f"{'='*50}")
            
        except ImportError:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️  Permissions app not available. Using Django's built-in permissions instead."
                )
            )
            self.create_django_permissions()
        except Exception as e:
            raise CommandError(f"Failed to create permissions: {str(e)}")

    def create_django_permissions(self):
        """Create Django built-in permissions as fallback"""
        from django.contrib.auth.models import Permission, ContentType
        from flows.models import Flow
        
        try:
            flow_content_type = ContentType.objects.get_for_model(Flow)
            
            django_permissions = [
                ('view_flow_details', 'Can view flow details'),
                ('create_flow', 'Can create flows'),
                ('edit_flow', 'Can edit flows'),
                ('delete_flow', 'Can delete flows'),
                ('activate_flow', 'Can activate flows'),
                ('execute_flow', 'Can execute flows'),
                ('approve_flow_steps', 'Can approve flow steps'),
                ('monitor_flows', 'Can monitor flow executions'),
            ]
            
            created_count = 0
            
            for codename, name in django_permissions:
                permission, created = Permission.objects.get_or_create(
                    codename=codename,
                    content_type=flow_content_type,
                    defaults={'name': name}
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ Created Django permission: {codename}")
                    )
            
            self.stdout.write(f"\n✅ Created {created_count} Django permissions")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Failed to create Django permissions: {str(e)}")
            )

    def list_flow_permissions(self):
        """List all flow-related permissions"""
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(self.style.HTTP_INFO("FLOW PERMISSIONS"))
        self.stdout.write(f"{'='*60}")
        
        try:
            # Try custom permissions first
            from permissions.models import Permission
            
            flow_permissions = Permission.objects.filter(
                name__startswith='flow:'
            ).order_by('name')
            
            if flow_permissions.exists():
                self.stdout.write("Custom Permissions:")
                for i, perm in enumerate(flow_permissions, 1):
                    self.stdout.write(f"  {i:2d}. {perm.name}")
                    self.stdout.write(f"      {perm.description}")
            else:
                self.stdout.write(self.style.WARNING("No custom flow permissions found"))
                
        except ImportError:
            # Fallback to Django permissions
            from django.contrib.auth.models import Permission, ContentType
            from flows.models import Flow
            
            try:
                flow_content_type = ContentType.objects.get_for_model(Flow)
                django_permissions = Permission.objects.filter(
                    content_type=flow_content_type
                ).order_by('codename')
                
                if django_permissions.exists():
                    self.stdout.write("Django Permissions:")
                    for i, perm in enumerate(django_permissions, 1):
                        self.stdout.write(f"  {i:2d}. {perm.codename}")
                        self.stdout.write(f"      {perm.name}")
                else:
                    self.stdout.write(self.style.WARNING("No Django flow permissions found"))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error listing permissions: {str(e)}"))
        
        self.stdout.write(f"{'='*60}")

    def assign_admin_permissions(self, username):
        """Assign all flow permissions to a user (admin level)"""
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' not found")
        
        self.stdout.write(f"Assigning admin flow permissions to: {username}")
        
        try:
            # Try custom permissions
            from permissions.models import Permission, UserPermission
            
            flow_permissions = Permission.objects.filter(name__startswith='flow:')
            assigned_count = 0
            
            with transaction.atomic():
                for permission in flow_permissions:
                    user_perm, created = UserPermission.objects.get_or_create(
                        user=user,
                        permission=permission,
                        defaults={'granted_by': user}  # Self-granted for setup
                    )
                    
                    if created:
                        assigned_count += 1
                        self.stdout.write(f"  ✅ {permission.name}")
                    else:
                        self.stdout.write(f"     {permission.name} (already assigned)")
            
            self.stdout.write(
                self.style.SUCCESS(f"\n✅ Assigned {assigned_count} permissions to {username}")
            )
            
        except ImportError:
            # Fallback to Django permissions
            from django.contrib.auth.models import Permission, ContentType
            from flows.models import Flow
            
            flow_content_type = ContentType.objects.get_for_model(Flow)
            flow_permissions = Permission.objects.filter(content_type=flow_content_type)
            
            assigned_permissions = []
            for permission in flow_permissions:
                if not user.user_permissions.filter(id=permission.id).exists():
                    user.user_permissions.add(permission)
                    assigned_permissions.append(permission.codename)
                    self.stdout.write(f"  ✅ {permission.codename}")
                else:
                    self.stdout.write(f"     {permission.codename} (already assigned)")
            
            self.stdout.write(
                self.style.SUCCESS(f"\n✅ Assigned {len(assigned_permissions)} Django permissions to {username}")
            )

    def assign_manager_permissions(self, username):
        """Assign manager-level flow permissions to a user"""
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' not found")
        
        self.stdout.write(f"Assigning manager flow permissions to: {username}")
        
        # Manager-level permissions (subset of admin)
        manager_permissions = [
            'flow:view',
            'flow:execute', 
            'flow:approve',
            'flow:monitor'
        ]
        
        try:
            # Try custom permissions
            from permissions.models import Permission, UserPermission
            
            permissions = Permission.objects.filter(name__in=manager_permissions)
            assigned_count = 0
            
            with transaction.atomic():
                for permission in permissions:
                    user_perm, created = UserPermission.objects.get_or_create(
                        user=user,
                        permission=permission,
                        defaults={'granted_by': user}  # Self-granted for setup
                    )
                    
                    if created:
                        assigned_count += 1
                        self.stdout.write(f"  ✅ {permission.name}")
                    else:
                        self.stdout.write(f"     {permission.name} (already assigned)")
            
            self.stdout.write(
                self.style.SUCCESS(f"\n✅ Assigned {assigned_count} manager permissions to {username}")
            )
            
        except ImportError:
            # Fallback to Django permissions
            from django.contrib.auth.models import Permission, ContentType
            from flows.models import Flow
            
            # Map to Django permission codenames
            django_manager_permissions = [
                'view_flow_details',
                'execute_flow',
                'approve_flow_steps',
                'monitor_flows'
            ]
            
            flow_content_type = ContentType.objects.get_for_model(Flow)
            permissions = Permission.objects.filter(
                content_type=flow_content_type,
                codename__in=django_manager_permissions
            )
            
            assigned_permissions = []
            for permission in permissions:
                if not user.user_permissions.filter(id=permission.id).exists():
                    user.user_permissions.add(permission)
                    assigned_permissions.append(permission.codename)
                    self.stdout.write(f"  ✅ {permission.codename}")
                else:
                    self.stdout.write(f"     {permission.codename} (already assigned)")
            
            self.stdout.write(
                self.style.SUCCESS(f"\n✅ Assigned {len(assigned_permissions)} manager permissions to {username}")
            )