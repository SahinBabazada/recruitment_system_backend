from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from .views import (
    InterviewRoundViewSet, InterviewViewSet, InterviewParticipantViewSet,
    InterviewQuestionViewSet, InterviewQuestionResponseViewSet,
    InterviewFeedbackTemplateViewSet
)

# Create the main router
router = DefaultRouter()
router.register(r'interview-rounds', InterviewRoundViewSet, basename='interview-round')
router.register(r'interviews', InterviewViewSet, basename='interview')
router.register(r'interview-questions', InterviewQuestionViewSet, basename='interview-question')
router.register(r'feedback-templates', InterviewFeedbackTemplateViewSet, basename='feedback-template')

# Create nested routers for interview-related resources
interviews_router = routers.NestedDefaultRouter(router, r'interviews', lookup='interview')
interviews_router.register(r'participants', InterviewParticipantViewSet, basename='interview-participants')
interviews_router.register(r'question-responses', InterviewQuestionResponseViewSet, basename='interview-question-responses')

urlpatterns = [
    # Main API endpoints
    path('api/', include(router.urls)),
    path('api/', include(interviews_router.urls)),
]

# Custom URL patterns for specific actions
urlpatterns += [
    # Interview Round specific endpoints
    path('api/interview-rounds/<int:pk>/questions/', 
         InterviewRoundViewSet.as_view({'get': 'questions'}), 
         name='interview-round-questions'),
    
    path('api/interview-rounds/<int:pk>/feedback-templates/', 
         InterviewRoundViewSet.as_view({'get': 'feedback_templates'}), 
         name='interview-round-feedback-templates'),
    
    path('api/interview-rounds/<int:pk>/statistics/', 
         InterviewRoundViewSet.as_view({'get': 'statistics'}), 
         name='interview-round-statistics'),
    
    # Interview specific endpoints
    path('api/interviews/<int:pk>/update-status/', 
         InterviewViewSet.as_view({'post': 'update_status'}), 
         name='interview-update-status'),
    
    path('api/interviews/<int:pk>/reschedule/', 
         InterviewViewSet.as_view({'post': 'reschedule'}), 
         name='interview-reschedule'),
    
    path('api/interviews/<int:pk>/cancel/', 
         InterviewViewSet.as_view({'post': 'cancel'}), 
         name='interview-cancel'),
    
    path('api/interviews/<int:pk>/add-participant/', 
         InterviewViewSet.as_view({'post': 'add_participant'}), 
         name='interview-add-participant'),
    
    path('api/interviews/<int:pk>/submit-feedback/', 
         InterviewViewSet.as_view({'post': 'submit_feedback'}), 
         name='interview-submit-feedback'),
    
    path('api/interviews/<int:pk>/feedback-summary/', 
         InterviewViewSet.as_view({'get': 'feedback_summary'}), 
         name='interview-feedback-summary'),
    
    path('api/interviews/dashboard-stats/', 
         InterviewViewSet.as_view({'get': 'dashboard_stats'}), 
         name='interview-dashboard-stats'),
    
    path('api/interviews/upcoming/', 
         InterviewViewSet.as_view({'get': 'upcoming'}), 
         name='interview-upcoming'),
    
    path('api/interviews/my-interviews/', 
         InterviewViewSet.as_view({'get': 'my_interviews'}), 
         name='interview-my-interviews'),
    
    # Interview Participant specific endpoints
    path('api/interviews/<int:interview_pk>/participants/<int:pk>/mark-attended/', 
         InterviewParticipantViewSet.as_view({'post': 'mark_attended'}), 
         name='interview-participant-mark-attended'),
    
    path('api/interviews/<int:interview_pk>/participants/<int:pk>/mark-left/', 
         InterviewParticipantViewSet.as_view({'post': 'mark_left'}), 
         name='interview-participant-mark-left'),
    
    # Interview Question specific endpoints
    path('api/interview-questions/<int:pk>/increment-usage/', 
         InterviewQuestionViewSet.as_view({'post': 'increment_usage'}), 
         name='interview-question-increment-usage'),
    
    path('api/interview-questions/by-round/', 
         InterviewQuestionViewSet.as_view({'get': 'by_round'}), 
         name='interview-questions-by-round'),
    
    # Feedback Template specific endpoints
    path('api/feedback-templates/<int:pk>/set-default/', 
         InterviewFeedbackTemplateViewSet.as_view({'post': 'set_default'}), 
         name='feedback-template-set-default'),
]

# API endpoints summary for documentation
"""
Interview API Endpoints:

Main Resources:
- GET/POST /api/interview-rounds/ - List/Create interview rounds
- GET/PUT/PATCH/DELETE /api/interview-rounds/{id}/ - Manage interview round
- GET/POST /api/interviews/ - List/Create interviews
- GET/PUT/PATCH/DELETE /api/interviews/{id}/ - Manage interview
- GET/POST /api/interview-questions/ - List/Create questions
- GET/PUT/PATCH/DELETE /api/interview-questions/{id}/ - Manage question
- GET/POST /api/feedback-templates/ - List/Create feedback templates
- GET/PUT/PATCH/DELETE /api/feedback-templates/{id}/ - Manage template

Interview Round Actions:
- GET /api/interview-rounds/{id}/questions/ - Get questions for round
- GET /api/interview-rounds/{id}/feedback-templates/ - Get templates for round
- GET /api/interview-rounds/{id}/statistics/ - Get round statistics

Interview Actions:
- POST /api/interviews/{id}/update-status/ - Update interview status
- POST /api/interviews/{id}/reschedule/ - Reschedule interview
- POST /api/interviews/{id}/cancel/ - Cancel interview
- POST /api/interviews/{id}/add-participant/ - Add participant
- POST /api/interviews/{id}/submit-feedback/ - Submit participant feedback
- GET /api/interviews/{id}/feedback-summary/ - Get feedback summary
- GET /api/interviews/dashboard-stats/ - Dashboard statistics
- GET /api/interviews/upcoming/ - Upcoming interviews
- GET /api/interviews/my-interviews/ - Current user's interviews

Interview Participants:
- GET/POST /api/interviews/{interview_id}/participants/ - List/Add participants
- GET/PUT/PATCH/DELETE /api/interviews/{interview_id}/participants/{id}/ - Manage participant
- POST /api/interviews/{interview_id}/participants/{id}/mark-attended/ - Mark attended
- POST /api/interviews/{interview_id}/participants/{id}/mark-left/ - Mark left

Question Responses:
- GET/POST /api/interviews/{interview_id}/question-responses/ - List/Create responses
- GET/PUT/PATCH/DELETE /api/interviews/{interview_id}/question-responses/{id}/ - Manage response

Question Management:
- POST /api/interview-questions/{id}/increment-usage/ - Increment usage count
- GET /api/interview-questions/by-round/ - Group questions by round

Template Management:
- POST /api/feedback-templates/{id}/set-default/ - Set as default template

Filter Parameters:

Interview Filters:
- search: Text search across multiple fields
- status, status__in: Filter by interview status
- scheduled_after, scheduled_before, scheduled_date_range: Filter by date
- is_upcoming, is_overdue, is_today, is_this_week: Time-based filters
- overall_score__gte, overall_score__lte: Filter by score range
- recommendation, recommendation__in: Filter by recommendation
- interview_round, interview_round__in: Filter by round
- candidate, candidate_name__icontains: Filter by candidate
- mpr, mpr_title__icontains: Filter by MPR
- location__icontains, is_online: Filter by location
- has_participants, participant_user, participant_role: Filter by participants
- has_feedback, has_complete_feedback: Filter by feedback status

Participant Filters:
- role, role__in: Filter by participant role
- attended: Filter by attendance
- has_individual_score: Filter by scoring status
- individual_score__gte, individual_score__lte: Filter by score range
- individual_recommendation: Filter by recommendation
- user, user_name__icontains: Filter by user

Question Filters:
- search: Text search in question content
- interview_round: Filter by round
- question_type, question_type__in: Filter by type
- difficulty_level, difficulty_level__in: Filter by difficulty
- is_active: Filter by active status
- usage_count__gte, usage_count__lte: Filter by usage
- has_follow_up_questions, has_ideal_answer_points: Filter by content

Example Usage:
GET /api/interviews/?status=scheduled&is_upcoming=true
GET /api/interviews/?candidate_name__icontains=john&overall_score__gte=4.0
GET /api/interviews/123/participants/?role=primary_interviewer
GET /api/interview-questions/?interview_round=1&question_type=technical
GET /api/interviews/?search=python&scheduled_date_range_after=2025-06-01

Request/Response Examples:

Create Interview:
POST /api/interviews/
{
    "candidate": 123,
    "mpr": 456,
    "interview_round": 1,
    "scheduled_date": "2025-06-15T10:00:00Z",
    "duration_minutes": 60,
    "location": "Online",
    "meeting_link": "https://meet.google.com/abc-def-ghi",
    "participants_data": [
        {"user_id": 1, "role": "primary_interviewer"},
        {"user_id": 2, "role": "technical_interviewer"}
    ]
}

Update Interview Status:
POST /api/interviews/123/update-status/
{
    "status": "completed",
    "actual_start_time": "2025-06-15T10:05:00Z",
    "actual_end_time": "2025-06-15T11:00:00Z"
}

Submit Feedback:
POST /api/interviews/123/submit-feedback/
{
    "individual_score": 4.5,
    "individual_feedback": "Strong technical skills, good communication",
    "individual_recommendation": "hire",
    "criteria_evaluations": [
        {
            "criteria_name": "Technical Skills",
            "score": 4.5,
            "comments": "Excellent problem-solving",
            "weight": 0.4
        },
        {
            "criteria_name": "Communication",
            "score": 4.0,
            "comments": "Clear and concise",
            "weight": 0.3
        }
    ]
}

Reschedule Interview:
POST /api/interviews/123/reschedule/
{
    "new_date": "2025-06-16T14:00:00Z",
    "new_location": "Conference Room A",
    "reason": "scheduling_conflict",
    "reason_details": "Interviewer had an emergency",
    "initiated_by_type": "recruiter"
}
"""