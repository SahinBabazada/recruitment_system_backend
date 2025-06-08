# permissions/management/__init__.py
# Empty file

# permissions/management/commands/__init__.py
# Empty file

# permissions/management/commands/create_default_permissions.py
from django.core.management.base import BaseCommand
from permissions.models import Permission, Role, RolePermission

class Command(BaseCommand):
    help = 'Create default permissions and roles for the recruitment system'

    def handle(self, *args, **options):
        self.stdout.write('Creating default permissions and roles...')
        
        # Define all permissions by module
        permissions_data = {
            # MPR (Manpower Requisition) permissions
            'mpr': [
                ('create', 'Create new MPR forms'),
                ('view', 'View MPR forms'),
                ('edit', 'Edit MPR forms'),
                ('delete', 'Delete MPR forms'),
                ('approve', 'Approve MPR forms'),
                ('reject', 'Reject MPR forms'),
                ('export', 'Export MPR data'),
            ],
            
             'user': [
                ('create', 'Create new users'),
                ('view', 'View user profiles'),
                ('edit', 'Edit user information'),
                ('delete', 'Delete users'),
                ('activate', 'Activate/Deactivate users'),
                ('reset_password', 'Reset user passwords'),
                ('view_all', 'View all users (bypass ownership)'),
            ],   

            # Interview permissions
            'interview': [
                ('create', 'Schedule interviews'),
                ('view', 'View interview details'),
                ('edit', 'Edit interview details'),
                ('delete', 'Cancel interviews'),
                ('conduct', 'Conduct interviews'),
                ('feedback', 'Provide interview feedback'),
                ('calendar', 'Manage interview calendar'),
            ],
            
            # Candidate permissions
            'candidate': [
                ('create', 'Add new candidates'),
                ('view', 'View candidate profiles'),
                ('edit', 'Edit candidate information'),
                ('delete', 'Delete candidate records'),
                ('search', 'Search candidates'),
                ('export', 'Export candidate data'),
                ('communicate', 'Communicate with candidates'),
            ],
            
            # Job Offer permissions
            'offer': [
                ('create', 'Create job offers'),
                ('view', 'View job offers'),
                ('edit', 'Edit job offers'),
                ('delete', 'Delete job offers'),
                ('approve', 'Approve job offers'),
                ('send', 'Send job offers'),
                ('negotiate', 'Negotiate offer terms'),
            ],
            
            # Email permissions
            'email': [
                ('view', 'View emails'),
                ('send', 'Send emails'),
                ('templates', 'Manage email templates'),
                ('bulk_send', 'Send bulk emails'),
            ],
            
            # Transfer & Promotion permissions
            'transfer': [
                ('create', 'Create transfer/promotion requests'),
                ('view', 'View transfer/promotion requests'),
                ('edit', 'Edit transfer/promotion requests'),
                ('delete', 'Delete transfer/promotion requests'),
                ('approve', 'Approve transfer/promotion requests'),
                ('process', 'Process transfer/promotion requests'),
            ],
            
            # User management permissions
            'user': [
                ('create', 'Create new users'),
                ('view', 'View user profiles'),
                ('edit', 'Edit user information'),
                ('delete', 'Delete users'),
                ('activate', 'Activate/Deactivate users'),
                ('reset_password', 'Reset user passwords'),
            ],
            
            # Role and Permission management
            'role': [
                ('create', 'Create new roles'),
                ('view', 'View roles'),
                ('edit', 'Edit roles'),
                ('delete', 'Delete roles'),
                ('assign', 'Assign roles to users'),
            ],
            
            'permission': [
                ('view', 'View permissions'),
                ('assign', 'Assign permissions'),
                ('revoke', 'Revoke permissions'),
            ],
            
            # Dashboard and Analytics
            'dashboard': [
                ('view', 'View dashboard'),
                ('analytics', 'View analytics'),
                ('reports', 'Generate reports'),
                ('export', 'Export reports'),
            ],
            
            # Settings permissions
            'settings': [
                ('view', 'View system settings'),
                ('edit', 'Edit system settings'),
                ('backup', 'Create system backups'),
                ('maintenance', 'System maintenance'),
            ],
            
            # System-level permissions (service permissions)
            'system': [
                ('admin', 'Full system administration'),
                ('manage_service_roles', 'Manage service roles and permissions'),
                ('audit', 'View system audit logs'),
                ('debug', 'System debugging'),
            ],
        }
        
        # Create permissions
        created_permissions = []
        for module, actions in permissions_data.items():
            for action, description in actions:
                permission_name = f"{module}:{action}"
                is_service = module == 'system'
                
                permission, created = Permission.objects.get_or_create(
                    name=permission_name,
                    defaults={
                        'description': description,
                        'module': module,
                        'action': action,
                        'is_service': is_service,
                    }
                )
                
                if created:
                    created_permissions.append(permission_name)
                    self.stdout.write(f"Created permission: {permission_name}")
        
        # Define default roles with their permissions
        roles_data = {
            'System Administrator': {
                'description': 'Full system access with all permissions',
                'permissions': [perm.name for perm in Permission.objects.all()],
                'is_service': True,
            },
            
            'HR Manager': {
                'description': 'Full HR operations management',
                'permissions': [
                    # MPR permissions
                    'mpr:create', 'mpr:view', 'mpr:edit', 'mpr:delete', 'mpr:approve', 'mpr:reject', 'mpr:export',
                    # Interview permissions
                    'interview:create', 'interview:view', 'interview:edit', 'interview:delete', 'interview:conduct', 'interview:feedback', 'interview:calendar',
                    # Candidate permissions  
                    'candidate:create', 'candidate:view', 'candidate:edit', 'candidate:delete', 'candidate:search', 'candidate:export', 'candidate:communicate',
                    # Offer permissions
                    'offer:create', 'offer:view', 'offer:edit', 'offer:delete', 'offer:approve', 'offer:send', 'offer:negotiate',
                    # Email permissions
                    'email:view', 'email:send', 'email:templates', 'email:bulk_send',
                    # Transfer permissions
                    'transfer:create', 'transfer:view', 'transfer:edit', 'transfer:delete', 'transfer:approve', 'transfer:process',
                    # User management (limited)
                    'user:view', 'user:edit', 'user:activate',
                    # Dashboard
                    'dashboard:view', 'dashboard:analytics', 'dashboard:reports', 'dashboard:export',
                ],
                'is_service': True,
            },
            
            'HR Specialist': {
                'description': 'HR operations with limited management permissions',
                'permissions': [
                    # MPR permissions (no approve/reject)
                    'mpr:create', 'mpr:view', 'mpr:edit', 'mpr:export',
                    # Interview permissions
                    'interview:create', 'interview:view', 'interview:edit', 'interview:conduct', 'interview:feedback', 'interview:calendar',
                    # Candidate permissions
                    'candidate:create', 'candidate:view', 'candidate:edit', 'candidate:search', 'candidate:export', 'candidate:communicate',
                    # Offer permissions (limited)
                    'offer:create', 'offer:view', 'offer:edit', 'offer:send',
                    # Email permissions
                    'email:view', 'email:send', 'email:templates',
                    # Transfer permissions (limited)
                    'transfer:create', 'transfer:view', 'transfer:edit',
                    # Dashboard
                    'dashboard:view', 'dashboard:analytics', 'dashboard:reports',
                ],
                'is_service': True,
            },
            
            'Recruiter': {
                'description': 'Focused on recruitment activities',
                'permissions': [
                    # MPR permissions (view only)
                    'mpr:view', 'mpr:export',
                    # Interview permissions
                    'interview:create', 'interview:view', 'interview:edit', 'interview:conduct', 'interview:feedback', 'interview:calendar',
                    # Candidate permissions
                    'candidate:create', 'candidate:view', 'candidate:edit', 'candidate:search', 'candidate:export', 'candidate:communicate',
                    # Offer permissions (limited)
                    'offer:view', 'offer:send',
                    # Email permissions
                    'email:view', 'email:send', 'email:templates',
                    # Dashboard
                    'dashboard:view', 'dashboard:analytics',
                ],
                'is_service': True,
            },
            
            'Hiring Manager': {
                'description': 'Managers who participate in hiring process',
                'permissions': [
                    # MPR permissions
                    'mpr:create', 'mpr:view', 'mpr:edit',
                    # Interview permissions
                    'interview:view', 'interview:conduct', 'interview:feedback', 'interview:calendar',
                    # Candidate permissions (limited)
                    'candidate:view', 'candidate:search',
                    # Offer permissions (limited)
                    'offer:view', 'offer:approve',
                    # Dashboard
                    'dashboard:view',
                ],
                'is_service': True,
            },
            
            'Interviewer': {
                'description': 'Staff who conduct interviews',
                'permissions': [
                    # Interview permissions (limited)
                    'interview:view', 'interview:conduct', 'interview:feedback', 'interview:calendar',
                    # Candidate permissions (view only)
                    'candidate:view',
                    # Dashboard
                    'dashboard:view',
                ],
                'is_service': True,
            },
            
            'Employee': {
                'description': 'Basic employee access',
                'permissions': [
                    # Transfer permissions (own requests)
                    'transfer:create', 'transfer:view',
                    # Dashboard (limited)
                    'dashboard:view',
                ],
                'is_service': True,
            },
            
            'Guest': {
                'description': 'Limited read-only access',
                'permissions': [
                    'dashboard:view',
                ],
                'is_service': True,
            },
        }
        
        # Create roles and assign permissions
        created_roles = []
        for role_name, role_data in roles_data.items():
            role, created = Role.objects.get_or_create(
                name=role_name,
                defaults={
                    'description': role_data['description'],
                    'is_service': role_data['is_service'],
                }
            )
            
            if created:
                created_roles.append(role_name)
                self.stdout.write(f"Created role: {role_name}")
            
            # Assign permissions to role
            for perm_name in role_data['permissions']:
                try:
                    permission = Permission.objects.get(name=perm_name)
                    role_permission, created = RolePermission.objects.get_or_create(
                        role=role,
                        permission=permission,
                    )
                    if created:
                        self.stdout.write(f"  Added permission {perm_name} to {role_name}")
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f"Permission {perm_name} not found for role {role_name}")
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {len(created_permissions)} permissions and {len(created_roles)} roles'
            )
        )