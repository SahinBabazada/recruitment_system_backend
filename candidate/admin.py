from django.contrib import admin
from .models import Candidate, CandidateEmail, EmailAttachment, CandidateMPR, CandidateStatusUpdate

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'hiring_status', 'overall_score', 'applied_at']
    list_filter = ['hiring_status', 'applied_at', 'current_company']
    search_fields = ['name', 'email', 'current_position']
    readonly_fields = ['applied_at', 'created_at', 'updated_at']

@admin.register(CandidateEmail)
class CandidateEmailAdmin(admin.ModelAdmin):
    list_display = ['candidate', 'subject', 'email_type', 'is_inbound', 'sent_at']
    list_filter = ['email_type', 'is_inbound', 'is_read']
    search_fields = ['subject', 'candidate__name']

admin.site.register(EmailAttachment)
admin.site.register(CandidateMPR)
admin.site.register(CandidateStatusUpdate)