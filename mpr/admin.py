# mpr/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Job, OrganizationalUnit, Location, EmploymentType, HiringReason,
    Employee, TechnicalSkill, Language, Competency, ContractDuration,
    MPR, MPRComment, MPRStatusHistory
)


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_active', 'created_at', 'created_by']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(OrganizationalUnit)
class OrganizationalUnitAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'parent', 'code', 'is_active']
    list_filter = ['type', 'is_active']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['created_at', 'updated_at']
    list_select_related = ['parent']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('parent')


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