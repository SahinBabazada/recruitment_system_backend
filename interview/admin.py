from django.contrib import admin
from .models import InterviewRound, Interview, InterviewParticipant, InterviewQuestion

@admin.register(InterviewRound)
class InterviewRoundAdmin(admin.ModelAdmin):
    list_display = ['name', 'sequence_order', 'typical_duration', 'is_active']
    list_filter = ['is_active', 'sequence_order']

@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ['candidate', 'interview_round', 'scheduled_date', 'status', 'overall_score']
    list_filter = ['status', 'interview_round', 'scheduled_date']
    search_fields = ['candidate__name', 'candidate__email']

@admin.register(InterviewQuestion)
class InterviewQuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'interview_round', 'question_type', 'difficulty_level', 'usage_count']
    list_filter = ['interview_round', 'question_type', 'difficulty_level', 'is_active']

admin.site.register(InterviewParticipant)