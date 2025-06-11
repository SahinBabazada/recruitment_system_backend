# candidate/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db import models
from django.forms import Textarea
from .models import (
    Candidate, CandidateWorkExperience, CandidateEducation,
    CandidateProject, CandidateReference, CandidateEmailConnection,
    CandidateAttachment, CandidateStatusUpdate, CandidateMPR
)


class CandidateWorkExperienceInline(admin.TabularInline):
    """Inline admin for work experience"""
    model = CandidateWorkExperience
    extra = 1
    fields = [
        'company_name', 'position_title', 'employment_type',
        'start_date', 'end_date', 'is_current', 'display_order'
    ]
    ordering = ['-start_date', 'display_order']


class CandidateEducationInline(admin.TabularInline):
    """Inline admin for education"""
    model = CandidateEducation
    extra = 1
    fields = [
        'institution_name', 'degree_type', 'field_of_study',
        'start_date', 'end_date', 'is_current', 'grade_gpa'
    ]
    ordering = ['-start_date']


class CandidateProjectInline(admin.StackedInline):
    """Inline admin for projects"""
    model = CandidateProject
    extra = 0
    fields = [
        'project_name', 'project_type', 'description',
        'technologies_used', 'start_date', 'end_date',
        'project_url', 'github_url', 'is_featured'
    ]
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 3, 'cols': 80})},
    }


class CandidateReferenceInline(admin.TabularInline):
    """Inline admin for references"""
    model = CandidateReference
    extra = 0
    fields = [
        'reference_name', 'reference_title', 'company_name',
        'relationship', 'email', 'permission_to_contact'
    ]


class CandidateAttachmentInline(admin.TabularInline):
    """Inline admin for attachments"""
    model = CandidateAttachment
    extra = 0
    fields = [
        'file_name', 'file_type', 'file_size_display',
        'is_primary_cv', 'is_latest_version', 'created_at'
    ]
    readonly_fields = ['file_size_display', 'created_at']
    
    def file_size_display(self, obj):
        """Format file size in human readable format"""
        if obj.file_size:
            size = obj.file_size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        return "-"
    file_size_display.short_description = "File Size"


class CandidateStatusUpdateInline(admin.TabularInline):
    """Inline admin for status updates"""
    model = CandidateStatusUpdate
    extra = 0
    fields = ['previous_status', 'new_status', 'reason', 'updated_by', 'updated_at']
    readonly_fields = ['updated_at']
    ordering = ['-updated_at']


class CandidateMPRInline(admin.TabularInline):
    """Inline admin for MPR applications"""
    model = CandidateMPR
    extra = 0
    fields = ['mpr', 'application_stage', 'primary_cv', 'applied_at']
    readonly_fields = ['applied_at']


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    """Enhanced admin for Candidate model"""
    
    list_display = [
        'name', 'email', 'current_position', 'current_company',
        'hiring_status_badge', 'overall_score', 'skill_match_percentage',
        'experience_years', 'applied_at', 'email_count', 'attachment_count'
    ]
    
    list_filter = [
        'hiring_status', 'experience_years', 'salary_currency',
        'applied_at', 'created_at', 'nationality'
    ]
    
    search_fields = [
        'name', 'email', 'phone', 'current_position', 
        'current_company', 'location'
    ]
    
    readonly_fields = [
        'applied_at', 'created_at', 'updated_at', 'email_count',
        'attachment_count', 'applications_count', 'latest_status_update'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                ('name', 'email'),
                ('phone', 'alternative_phone'),
                ('location', 'nationality'),
                'address',
                'date_of_birth'
            )
        }),
        ('Professional Information', {
            'fields': (
                ('current_position', 'current_company'),
                'professional_summary',
                'experience_years',
                ('professional_skills', 'technical_skills'),
                'soft_skills',
                'languages',
                'certifications'
            )
        }),
        ('Online Presence', {
            'fields': (
                'linkedin_url',
                'portfolio_url',
                'github_url',
                'personal_website'
            ),
            'classes': ('collapse',)
        }),
        ('Hiring Information', {
            'fields': (
                'hiring_status',
                ('overall_score', 'skill_match_percentage'),
                ('matched_skills_count', 'total_skills_count'),
                'latest_status_update'
            )
        }),
        ('Salary & Availability', {
            'fields': (
                ('salary_expectation', 'salary_currency'),
                ('availability_date', 'notice_period_days')
            )
        }),
        ('Internal Notes', {
            'fields': ('internal_notes',),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': (
                ('email_count', 'attachment_count', 'applications_count'),
                ('applied_at', 'created_at', 'updated_at')
            ),
            'classes': ('collapse',)
        })
    )
    
    inlines = [
        CandidateWorkExperienceInline,
        CandidateEducationInline,
        CandidateProjectInline,
        CandidateReferenceInline,
        CandidateAttachmentInline,
        CandidateStatusUpdateInline,
        CandidateMPRInline
    ]
    
    actions = ['mark_as_screening', 'mark_as_portfolio_review', 'mark_as_rejected']
    
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 4, 'cols': 80})},
        models.JSONField: {'widget': Textarea(attrs={'rows': 3, 'cols': 80})},
    }
    
    def hiring_status_badge(self, obj):
        """Display hiring status with color coding"""
        colors = {
            'applied': '#17a2b8',
            'screening': '#ffc107',
            'portfolio_review': '#fd7e14',
            'phone_interview': '#6f42c1',
            'technical_interview': '#6610f2',
            'final_interview': '#e83e8c',
            'reference_check': '#20c997',
            'offer_pending': '#007bff',
            'offer_accepted': '#28a745',
            'offer_declined': '#dc3545',
            'rejected': '#6c757d',
            'on_hold': '#ffc107',
            'withdrawn': '#6c757d'
        }
        
        color = colors.get(obj.hiring_status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_hiring_status_display()
        )
    hiring_status_badge.short_description = 'Status'
    hiring_status_badge.admin_order_field = 'hiring_status'
    
    def email_count(self, obj):
        """Count of email connections"""
        count = obj.email_connections.count()
        if count > 0:
            url = reverse('admin:candidate_candidateemailconnection_changelist')
            return format_html(
                '<a href="{}?candidate__id__exact={}">{} emails</a>',
                url, obj.pk, count
            )
        return "0 emails"
    email_count.short_description = 'Emails'
    
    def attachment_count(self, obj):
        """Count of attachments"""
        count = obj.attachments.count()
        primary_cv = obj.attachments.filter(is_primary_cv=True).first()
        
        if count > 0:
            url = reverse('admin:candidate_candidateattachment_changelist')
            cv_indicator = " (📄 CV)" if primary_cv else ""
            return format_html(
                '<a href="{}?candidate__id__exact={}">{} files{}</a>',
                url, obj.pk, count, cv_indicator
            )
        return "0 files"
    attachment_count.short_description = 'Files'
    
    def applications_count(self, obj):
        """Count of MPR applications"""
        return obj.mpr_applications.count()
    applications_count.short_description = 'Applications'
    
    def latest_status_update(self, obj):
        """Latest status update"""
        latest = obj.status_updates.first()
        if latest:
            return f"{latest.new_status} ({latest.updated_at.strftime('%Y-%m-%d')})"
        return "-"
    latest_status_update.short_description = 'Latest Update'
    
    # Custom actions
    def mark_as_screening(self, request, queryset):
        """Mark selected candidates as screening"""
        updated = 0
        for candidate in queryset:
            if candidate.hiring_status != 'screening':
                CandidateStatusUpdate.objects.create(
                    candidate=candidate,
                    previous_status=candidate.hiring_status,
                    new_status='screening',
                    reason='Bulk update via admin',
                    updated_by=request.user
                )
                candidate.hiring_status = 'screening'
                candidate.save()
                updated += 1
        
        self.message_user(request, f'{updated} candidates marked as screening.')
    mark_as_screening.short_description = "Mark as Screening"
    
    def mark_as_portfolio_review(self, request, queryset):
        """Mark selected candidates as portfolio review"""
        updated = 0
        for candidate in queryset:
            if candidate.hiring_status != 'portfolio_review':
                CandidateStatusUpdate.objects.create(
                    candidate=candidate,
                    previous_status=candidate.hiring_status,
                    new_status='portfolio_review',
                    reason='Bulk update via admin',
                    updated_by=request.user
                )
                candidate.hiring_status = 'portfolio_review'
                candidate.save()
                updated += 1
        
        self.message_user(request, f'{updated} candidates marked as portfolio review.')
    mark_as_portfolio_review.short_description = "Mark as Portfolio Review"
    
    def mark_as_rejected(self, request, queryset):
        """Mark selected candidates as rejected"""
        updated = 0
        for candidate in queryset:
            if candidate.hiring_status != 'rejected':
                CandidateStatusUpdate.objects.create(
                    candidate=candidate,
                    previous_status=candidate.hiring_status,
                    new_status='rejected',
                    reason='Bulk rejection via admin',
                    updated_by=request.user
                )
                candidate.hiring_status = 'rejected'
                candidate.save()
                updated += 1
        
        self.message_user(request, f'{updated} candidates marked as rejected.')
    mark_as_rejected.short_description = "Mark as Rejected"


@admin.register(CandidateWorkExperience)
class CandidateWorkExperienceAdmin(admin.ModelAdmin):
    """Admin for work experience"""
    
    list_display = [
        'candidate_name', 'company_name', 'position_title',
        'employment_type', 'start_date', 'end_date', 'is_current'
    ]
    
    list_filter = ['employment_type', 'is_current', 'start_date']
    
    search_fields = [
        'candidate__name', 'candidate__email', 'company_name',
        'position_title', 'location'
    ]
    
    raw_id_fields = ['candidate']
    
    def candidate_name(self, obj):
        """Display candidate name with link"""
        url = reverse('admin:candidate_candidate_change', args=[obj.candidate.pk])
        return format_html('<a href="{}">{}</a>', url, obj.candidate.name)
    candidate_name.short_description = 'Candidate'
    candidate_name.admin_order_field = 'candidate__name'


@admin.register(CandidateEducation)
class CandidateEducationAdmin(admin.ModelAdmin):
    """Admin for education"""
    
    list_display = [
        'candidate_name', 'institution_name', 'degree_type',
        'field_of_study', 'start_date', 'end_date', 'is_current'
    ]
    
    list_filter = ['degree_type', 'is_current', 'start_date']
    
    search_fields = [
        'candidate__name', 'candidate__email', 'institution_name',
        'field_of_study', 'specialization'
    ]
    
    raw_id_fields = ['candidate']
    
    def candidate_name(self, obj):
        """Display candidate name with link"""
        url = reverse('admin:candidate_candidate_change', args=[obj.candidate.pk])
        return format_html('<a href="{}">{}</a>', url, obj.candidate.name)
    candidate_name.short_description = 'Candidate'
    candidate_name.admin_order_field = 'candidate__name'


@admin.register(CandidateProject)
class CandidateProjectAdmin(admin.ModelAdmin):
    """Admin for projects"""
    
    list_display = [
        'candidate_name', 'project_name', 'project_type',
        'is_featured', 'start_date', 'end_date', 'has_links'
    ]
    
    list_filter = ['project_type', 'is_featured', 'start_date']
    
    search_fields = [
        'candidate__name', 'candidate__email', 'project_name', 'description'
    ]
    
    raw_id_fields = ['candidate']
    
    def candidate_name(self, obj):
        """Display candidate name with link"""
        url = reverse('admin:candidate_candidate_change', args=[obj.candidate.pk])
        return format_html('<a href="{}">{}</a>', url, obj.candidate.name)
    candidate_name.short_description = 'Candidate'
    candidate_name.admin_order_field = 'candidate__name'
    
    def has_links(self, obj):
        """Show if project has external links"""
        links = []
        if obj.project_url:
            links.append('🌐')
        if obj.github_url:
            links.append('📦')
        if obj.demo_url:
            links.append('🎬')
        return ' '.join(links) if links else '-'
    has_links.short_description = 'Links'


@admin.register(CandidateEmailConnection)
class CandidateEmailConnectionAdmin(admin.ModelAdmin):
    """Admin for email connections"""
    
    list_display = [
        'candidate_name', 'email_subject', 'email_type',
        'is_inbound', 'requires_response', 'is_responded',
        'email_date', 'has_attachments'
    ]
    
    list_filter = [
        'email_type', 'is_inbound', 'requires_response',
        'is_responded', 'created_at'
    ]
    
    search_fields = [
        'candidate__name', 'candidate__email',
        'email_message__subject', 'email_message__from_email'
    ]
    
    raw_id_fields = ['candidate', 'email_message']
    
    def candidate_name(self, obj):
        """Display candidate name with link"""
        url = reverse('admin:candidate_candidate_change', args=[obj.candidate.pk])
        return format_html('<a href="{}">{}</a>', url, obj.candidate.name)
    candidate_name.short_description = 'Candidate'
    candidate_name.admin_order_field = 'candidate__name'
    
    def email_subject(self, obj):
        """Display email subject (truncated)"""
        subject = obj.email_message.subject
        if len(subject) > 50:
            return f"{subject[:50]}..."
        return subject
    email_subject.short_description = 'Subject'
    
    def email_date(self, obj):
        """Display email date"""
        return obj.email_message.received_datetime.strftime('%Y-%m-%d %H:%M')
    email_date.short_description = 'Date'
    email_date.admin_order_field = 'email_message__received_datetime'
    
    def has_attachments(self, obj):
        """Show if email has attachments"""
        count = obj.attachments.count()
        return f"📎 {count}" if count > 0 else "-"
    has_attachments.short_description = 'Attachments'


@admin.register(CandidateAttachment)
class CandidateAttachmentAdmin(admin.ModelAdmin):
    """Admin for attachments"""
    
    list_display = [
        'candidate_name', 'file_name_short', 'file_type',
        'file_size_display', 'is_primary_cv', 'is_latest_version',
        'uploaded_date', 'download_link'
    ]
    
    list_filter = [
        'file_type', 'is_primary_cv', 'is_latest_version',
        'is_processed', 'created_at'
    ]
    
    search_fields = [
        'candidate__name', 'candidate__email',
        'file_name', 'original_file_name', 'description'
    ]
    
    raw_id_fields = ['candidate', 'email_connection', 'uploaded_by']
    
    def candidate_name(self, obj):
        """Display candidate name with link"""
        url = reverse('admin:candidate_candidate_change', args=[obj.candidate.pk])
        return format_html('<a href="{}">{}</a>', url, obj.candidate.name)
    candidate_name.short_description = 'Candidate'
    candidate_name.admin_order_field = 'candidate__name'
    
    def file_name_short(self, obj):
        """Display shortened file name"""
        name = obj.original_file_name or obj.file_name
        if len(name) > 30:
            return f"{name[:30]}..."
        return name
    file_name_short.short_description = 'File Name'
    
    def file_size_display(self, obj):
        """Format file size in human readable format"""
        if obj.file_size:
            size = obj.file_size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        return "-"
    file_size_display.short_description = "Size"
    
    def uploaded_date(self, obj):
        """Display upload date"""
        return obj.created_at.strftime('%Y-%m-%d')
    uploaded_date.short_description = 'Uploaded'
    uploaded_date.admin_order_field = 'created_at'
    
    def download_link(self, obj):
        """Provide download link"""
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">📥 Download</a>',
                obj.file.url
            )
        return "-"
    download_link.short_description = 'Download'


@admin.register(CandidateStatusUpdate)
class CandidateStatusUpdateAdmin(admin.ModelAdmin):
    """Admin for status updates"""
    
    list_display = [
        'candidate_name', 'status_change', 'updated_by_name',
        'updated_at', 'reason_short'
    ]
    
    list_filter = ['previous_status', 'new_status', 'updated_at']
    
    search_fields = [
        'candidate__name', 'candidate__email', 'reason',
        'updated_by__first_name', 'updated_by__last_name'
    ]
    
    raw_id_fields = ['candidate', 'updated_by']
    
    def candidate_name(self, obj):
        """Display candidate name with link"""
        url = reverse('admin:candidate_candidate_change', args=[obj.candidate.pk])
        return format_html('<a href="{}">{}</a>', url, obj.candidate.name)
    candidate_name.short_description = 'Candidate'
    candidate_name.admin_order_field = 'candidate__name'
    
    def status_change(self, obj):
        """Display status change with colors"""
        return format_html(
            '{} → <strong>{}</strong>',
            obj.get_previous_status_display(),
            obj.get_new_status_display()
        )
    status_change.short_description = 'Status Change'
    
    def updated_by_name(self, obj):
        """Display updated by name"""
        return obj.updated_by.get_full_name() if obj.updated_by else 'System'
    updated_by_name.short_description = 'Updated By'
    updated_by_name.admin_order_field = 'updated_by__first_name'
    
    def reason_short(self, obj):
        """Display shortened reason"""
        if obj.reason:
            if len(obj.reason) > 50:
                return f"{obj.reason[:50]}..."
            return obj.reason
        return "-"
    reason_short.short_description = 'Reason'


@admin.register(CandidateMPR)
class CandidateMPRAdmin(admin.ModelAdmin):
    """Admin for MPR applications"""
    
    list_display = [
        'candidate_name', 'mpr_number', 'mpr_title',
        'application_stage', 'has_primary_cv', 'applied_at'
    ]
    
    list_filter = ['application_stage', 'applied_at']
    
    search_fields = [
        'candidate__name', 'candidate__email',
        'mpr__mpr_number', 'mpr__job_title__title'
    ]
    
    raw_id_fields = ['candidate', 'mpr', 'primary_cv', 'updated_by']
    
    def candidate_name(self, obj):
        """Display candidate name with link"""
        url = reverse('admin:candidate_candidate_change', args=[obj.candidate.pk])
        return format_html('<a href="{}">{}</a>', url, obj.candidate.name)
    candidate_name.short_description = 'Candidate'
    candidate_name.admin_order_field = 'candidate__name'
    
    def mpr_number(self, obj):
        """Display MPR number with link"""
        if obj.mpr:
            # Adjust this URL pattern based on your MPR admin setup
            try:
                url = reverse('admin:mpr_mpr_change', args=[obj.mpr.pk])
                return format_html('<a href="{}">{}</a>', url, obj.mpr.mpr_number)
            except:
                return obj.mpr.mpr_number
        return "-"
    mpr_number.short_description = 'MPR Number'
    
    def mpr_title(self, obj):
        """Display MPR job title"""
        if obj.mpr and hasattr(obj.mpr, 'job_title') and obj.mpr.job_title:
            return obj.mpr.job_title.title
        return "-"
    mpr_title.short_description = 'Position'
    
    def has_primary_cv(self, obj):
        """Show if has primary CV"""
        return "✓" if obj.primary_cv else "✗"
    has_primary_cv.short_description = 'CV'
    has_primary_cv.boolean = True


@admin.register(CandidateReference)
class CandidateReferenceAdmin(admin.ModelAdmin):
    """Admin for candidate references"""
    
    list_display = [
        'candidate_name', 'reference_name', 'reference_title',
        'company_name', 'relationship', 'permission_to_contact'
    ]
    
    list_filter = ['relationship', 'permission_to_contact']
    
    search_fields = [
        'candidate__name', 'candidate__email', 'reference_name',
        'company_name', 'reference_title'
    ]
    
    raw_id_fields = ['candidate']
    
    def candidate_name(self, obj):
        """Display candidate name with link"""
        url = reverse('admin:candidate_candidate_change', args=[obj.candidate.pk])
        return format_html('<a href="{}">{}</a>', url, obj.candidate.name)
    candidate_name.short_description = 'Candidate'
    candidate_name.admin_order_field = 'candidate__name'