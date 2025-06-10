# mpr/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Job, OrganizationalUnit, Location, EmploymentType, HiringReason,
    Employee, TechnicalSkill, Language, Competency, ContractDuration,
    MPR, MPRComment, MPRStatusHistory, Recruiter, Manager, BudgetHolder, BudgetSponsor
)


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_active', 'created_at', 'created_by']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']

# @admin.register(OrganizationalUnit)
# class OrganizationalUnitAdmin(admin.ModelAdmin):
#     list_display = ['name', 'type', 'parent', 'code', 'is_active']
#     list_filter = ['type', 'is_active']
#     search_fields = ['name', 'code', 'description']
#     readonly_fields = ['created_at', 'updated_at']
#     list_select_related = ['parent']
    
#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related('parent')

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'location_type', 'city', 'country', 'is_active']
    list_filter = ['location_type', 'is_active', 'country']
    search_fields = ['name', 'city', 'country', 'address']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(EmploymentType)
class EmploymentTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'is_default']
    list_filter = ['is_active', 'is_default']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(HiringReason)
class HiringReasonAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'is_default']
    list_filter = ['is_active', 'is_default']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'full_name', 'email', 'department', 'position', 'is_active']
    list_filter = ['is_active', 'department', 'location', 'hire_date']
    search_fields = ['employee_id', 'first_name', 'last_name', 'email']
    readonly_fields = ['created_at', 'updated_at']
    list_select_related = ['department', 'position', 'location']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('department', 'position', 'location')

@admin.register(TechnicalSkill)
class TechnicalSkillAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active', 'created_by']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'category', 'description']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Competency)
class CompetencyAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active', 'created_by']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'category', 'description']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(ContractDuration)
class ContractDurationAdmin(admin.ModelAdmin):
    list_display = ['name', 'months', 'is_active', 'is_default']
    list_filter = ['is_active', 'is_default']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']

class MPRCommentInline(admin.TabularInline):
    model = MPRComment
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    fields = ['user', 'comment', 'is_internal', 'created_at']

class MPRStatusHistoryInline(admin.TabularInline):
    model = MPRStatusHistory
    extra = 0
    readonly_fields = ['changed_at']
    fields = ['from_status', 'to_status', 'changed_by', 'reason', 'changed_at']

@admin.register(MPR)
class MPRAdmin(admin.ModelAdmin):
    list_display = [
        'mpr_number', 'job_title', 'department', 'status', 'priority',
        'created_by', 'desired_start_date', 'created_at'
    ]
    list_filter = [
        'status', 'priority', 'employment_type', 'hiring_reason',
        'department', 'location', 'created_at', 'desired_start_date'
    ]
    search_fields = [
        'mpr_number', 'job_title__title', 'department__name',
        'created_by__username', 'business_justification'
    ]
    readonly_fields = [
        'mpr_number', 'created_at', 'updated_at', 'approved_at', 'rejected_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('mpr_number', 'status', 'priority')
        }),
        ('Position Information', {
            'fields': (
                'job_title', 'department', 'division', 'unit', 'location',
                'desired_start_date', 'employment_type', 'hiring_reason',
                'replaced_employee', 'business_justification'
            )
        }),
        ('Requirements', {
            'fields': (
                'education_requirements', 'technical_skills', 'required_languages',
                'core_competencies', 'assessment_requirements', 'contract_duration'
            )
        }),
        ('Approval Information', {
            'fields': (
                'recruiter', 'budget_holder', 'proposed_candidate'
            )
        }),
        ('Audit Information', {
            'fields': (
                'created_by', 'created_at', 'updated_at', 'updated_by',
                'approved_by', 'approved_at', 'rejected_by', 'rejected_at',
                'rejection_reason'
            ),
            'classes': ('collapse',)
        })
    )
    
    filter_horizontal = ['technical_skills', 'required_languages', 'core_competencies']
    inlines = [MPRCommentInline, MPRStatusHistoryInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'job_title', 'department', 'division', 'unit', 'location',
            'employment_type', 'hiring_reason', 'replaced_employee',
            'contract_duration', 'created_by', 'updated_by', 'approved_by', 'rejected_by'
        ).prefetch_related('technical_skills', 'required_languages', 'core_competencies')

    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        else:  # Updating existing object
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(MPRComment)
class MPRCommentAdmin(admin.ModelAdmin):
    list_display = ['mpr', 'user', 'comment_preview', 'is_internal', 'created_at']
    list_filter = ['is_internal', 'created_at']
    search_fields = ['mpr__mpr_number', 'user__username', 'comment']
    readonly_fields = ['created_at', 'updated_at']
    list_select_related = ['mpr', 'user']
    
    def comment_preview(self, obj):
        return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
    comment_preview.short_description = 'Comment'

@admin.register(MPRStatusHistory)
class MPRStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['mpr', 'from_status', 'to_status', 'changed_by', 'changed_at']
    list_filter = ['from_status', 'to_status', 'changed_at']
    search_fields = ['mpr__mpr_number', 'changed_by__username', 'reason']
    readonly_fields = ['changed_at']
    list_select_related = ['mpr', 'changed_by']
# ----------
# mpr/admin.py (Updated with new role models)

class RecruiterInline(admin.TabularInline):
    model = Recruiter
    extra = 0
    fields = ['user', 'is_primary', 'specialization', 'is_active']
    readonly_fields = ['assigned_at']

class ManagerInline(admin.TabularInline):
    model = Manager
    extra = 0
    fields = ['user', 'is_primary', 'manager_type', 'is_active']
    readonly_fields = ['assigned_at']

class BudgetHolderInline(admin.TabularInline):
    model = BudgetHolder
    extra = 0
    fields = ['user', 'is_primary', 'budget_type', 'budget_limit', 'is_active']
    readonly_fields = ['assigned_at']

class BudgetSponsorInline(admin.TabularInline):
    model = BudgetSponsor
    extra = 0
    fields = ['user', 'is_primary', 'sponsor_level', 'approval_limit', 'is_active']
    readonly_fields = ['assigned_at']

@admin.register(OrganizationalUnit)
class OrganizationalUnitAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'type', 'parent', 'code', 'location', 'current_headcount', 
        'headcount_limit', 'headcount_utilization_display', 'primary_roles_summary', 'is_active'
    ]
    list_filter = ['type', 'is_active', 'location', 'created_at']
    search_fields = ['name', 'code', 'description', 'cost_center']
    readonly_fields = ['created_at', 'updated_at', 'current_headcount', 'headcount_utilization']
    list_select_related = ['parent', 'location', 'created_by']
    inlines = [RecruiterInline, ManagerInline, BudgetHolderInline, BudgetSponsorInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'type', 'parent', 'code', 'description', 'is_active')
        }),
        ('Location & Budget', {
            'fields': ('location', 'cost_center')
        }),
        ('Headcount Management', {
            'fields': ('headcount_limit', 'current_headcount', 'headcount_utilization'),
            'classes': ('collapse',)
        }),
        ('Primary Role Assignments', {
            'fields': (
                'primary_recruiter', 'primary_manager', 
                'primary_budget_holder', 'primary_budget_sponsor'
            ),
            'description': 'Quick assignment of primary roles. Use the role assignment tables below for detailed management.'
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'parent', 'location', 'created_by',
            'primary_recruiter', 'primary_manager', 
            'primary_budget_holder', 'primary_budget_sponsor'
        ).prefetch_related(
            'recruiters', 'managers', 'budget_holders', 'budget_sponsors'
        )

    def headcount_utilization_display(self, obj):
        if not obj.headcount_limit:
            return '-'
        utilization = obj.headcount_utilization
        if utilization > 100:
            color = 'red'
        elif utilization >= 90:
            color = 'orange'
        else:
            color = 'green'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, utilization
        )
    headcount_utilization_display.short_description = 'Utilization'

    def primary_roles_summary(self, obj):
        roles = []
        if obj.primary_recruiter:
            roles.append('R')
        if obj.primary_manager:
            roles.append('M')
        if obj.primary_budget_holder:
            roles.append('BH')
        if obj.primary_budget_sponsor:
            roles.append('BS')
        
        if not roles:
            return format_html('<span style="color: red;">None</span>')
        
        return format_html(
            '<span style="color: green;">{}</span>',
            ', '.join(roles)
        )
    primary_roles_summary.short_description = 'Primary Roles'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(Recruiter)
class RecruiterAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'organizational_unit', 'is_primary', 'specialization', 
        'is_active', 'assigned_at', 'assigned_by'
    ]
    list_filter = ['is_primary', 'is_active', 'assigned_at', 'organizational_unit__type']
    search_fields = [
        'user__first_name', 'user__last_name', 'user__username',
        'organizational_unit__name', 'specialization'
    ]
    readonly_fields = ['assigned_at']
    list_select_related = ['user', 'organizational_unit', 'assigned_by']
    
    fieldsets = (
        ('Assignment', {
            'fields': ('user', 'organizational_unit', 'is_primary', 'is_active')
        }),
        ('Details', {
            'fields': ('specialization',)
        }),
        ('Metadata', {
            'fields': ('assigned_by', 'assigned_at')
        })
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.assigned_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(Manager)
class ManagerAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'organizational_unit', 'is_primary', 'manager_type', 
        'is_active', 'assigned_at', 'assigned_by'
    ]
    list_filter = ['is_primary', 'manager_type', 'is_active', 'assigned_at', 'organizational_unit__type']
    search_fields = [
        'user__first_name', 'user__last_name', 'user__username',
        'organizational_unit__name'
    ]
    readonly_fields = ['assigned_at']
    list_select_related = ['user', 'organizational_unit', 'assigned_by']
    
    fieldsets = (
        ('Assignment', {
            'fields': ('user', 'organizational_unit', 'is_primary', 'is_active')
        }),
        ('Details', {
            'fields': ('manager_type',)
        }),
        ('Metadata', {
            'fields': ('assigned_by', 'assigned_at')
        })
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.assigned_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(BudgetHolder)
class BudgetHolderAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'organizational_unit', 'is_primary', 'budget_type', 
        'budget_limit_display', 'is_active', 'assigned_at', 'assigned_by'
    ]
    list_filter = ['is_primary', 'budget_type', 'is_active', 'assigned_at', 'organizational_unit__type']
    search_fields = [
        'user__first_name', 'user__last_name', 'user__username',
        'organizational_unit__name'
    ]
    readonly_fields = ['assigned_at']
    list_select_related = ['user', 'organizational_unit', 'assigned_by']
    
    fieldsets = (
        ('Assignment', {
            'fields': ('user', 'organizational_unit', 'is_primary', 'is_active')
        }),
        ('Budget Details', {
            'fields': ('budget_type', 'budget_limit')
        }),
        ('Metadata', {
            'fields': ('assigned_by', 'assigned_at')
        })
    )

    def budget_limit_display(self, obj):
        if obj.budget_limit:
            return f"${obj.budget_limit:,.0f}"
        return "-"
    budget_limit_display.short_description = 'Budget Limit'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.assigned_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(BudgetSponsor)
class BudgetSponsorAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'organizational_unit', 'is_primary', 'sponsor_level', 
        'approval_limit_display', 'is_active', 'assigned_at', 'assigned_by'
    ]
    list_filter = ['is_primary', 'sponsor_level', 'is_active', 'assigned_at', 'organizational_unit__type']
    search_fields = [
        'user__first_name', 'user__last_name', 'user__username',
        'organizational_unit__name'
    ]
    readonly_fields = ['assigned_at']
    list_select_related = ['user', 'organizational_unit', 'assigned_by']
    
    fieldsets = (
        ('Assignment', {
            'fields': ('user', 'organizational_unit', 'is_primary', 'is_active')
        }),
        ('Sponsor Details', {
            'fields': ('sponsor_level', 'approval_limit')
        }),
        ('Metadata', {
            'fields': ('assigned_by', 'assigned_at')
        })
    )

    def approval_limit_display(self, obj):
        if obj.approval_limit:
            return f"${obj.approval_limit:,.0f}"
        return "-"
    approval_limit_display.short_description = 'Approval Limit'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.assigned_by = request.user
        super().save_model(request, obj, form, change)

# Admin actions for bulk operations
@admin.action(description='Mark selected organizational units as active')
def make_active(modeladmin, request, queryset):
    updated = queryset.update(is_active=True)
    modeladmin.message_user(request, f'{updated} organizational units were marked as active.')

@admin.action(description='Mark selected organizational units as inactive')
def make_inactive(modeladmin, request, queryset):
    updated = queryset.update(is_active=False)
    modeladmin.message_user(request, f'{updated} organizational units were marked as inactive.')

@admin.action(description='Update headcount for selected units')
def update_headcount(modeladmin, request, queryset):
    updated = 0
    for unit in queryset:
        unit.update_headcount()
        updated += 1
    modeladmin.message_user(request, f'Headcount updated for {updated} organizational units.')

# Add actions to OrganizationalUnitAdmin
OrganizationalUnitAdmin.actions = [make_active, make_inactive, update_headcount]

# Bulk actions for role assignments
@admin.action(description='Activate selected role assignments')
def activate_roles(modeladmin, request, queryset):
    updated = queryset.update(is_active=True)
    modeladmin.message_user(request, f'{updated} role assignments were activated.')

@admin.action(description='Deactivate selected role assignments')
def deactivate_roles(modeladmin, request, queryset):
    updated = queryset.update(is_active=False)
    modeladmin.message_user(request, f'{updated} role assignments were deactivated.')

# Add actions to role admin classes
RecruiterAdmin.actions = [activate_roles, deactivate_roles]
ManagerAdmin.actions = [activate_roles, deactivate_roles]
BudgetHolderAdmin.actions = [activate_roles, deactivate_roles]
BudgetSponsorAdmin.actions = [activate_roles, deactivate_roles]

# Customize admin site
admin.site.site_header = "Recruitment System Administration"
admin.site.site_title = "Recruitment Admin"
admin.site.index_title = "Welcome to Recruitment System Administration"