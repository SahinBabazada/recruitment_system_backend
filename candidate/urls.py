from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

from .views import (
    CandidateViewSet, CandidateEmailViewSet, EmailAttachmentViewSet,
    CandidateMPRViewSet
)

# Create the main router
router = DefaultRouter()
router.register(r'candidates', CandidateViewSet, basename='candidate')

# Create nested routers for candidate-related resources
candidates_router = routers.NestedDefaultRouter(router, r'candidates', lookup='candidate')
candidates_router.register(r'emails', CandidateEmailViewSet, basename='candidate-emails')
candidates_router.register(r'attachments', EmailAttachmentViewSet, basename='candidate-attachments')
candidates_router.register(r'mpr-applications', CandidateMPRViewSet, basename='candidate-mpr-applications')

# Create nested router for email attachments
emails_router = routers.NestedDefaultRouter(candidates_router, r'emails', lookup='email')
emails_router.register(r'attachments', EmailAttachmentViewSet, basename='candidate-email-attachments')

urlpatterns = [
    # Main API endpoints
    path('api/', include(router.urls)),
    path('api/', include(candidates_router.urls)),
    path('api/', include(emails_router.urls)),
]

# Custom URL patterns for specific actions
urlpatterns += [
    # Candidate-specific endpoints
    path('api/candidates/<int:pk>/update-status/', 
         CandidateViewSet.as_view({'post': 'update_status'}), 
         name='candidate-update-status'),
    
    path('api/candidates/<int:pk>/calculate-scores/', 
         CandidateViewSet.as_view({'post': 'calculate_scores'}), 
         name='candidate-calculate-scores'),
    
    path('api/candidates/<int:pk>/update-skill-matching/', 
         CandidateViewSet.as_view({'post': 'update_skill_matching'}), 
         name='candidate-update-skill-matching'),
    
    path('api/candidates/<int:pk>/timeline/', 
         CandidateViewSet.as_view({'get': 'timeline'}), 
         name='candidate-timeline'),
    
    path('api/candidates/dashboard-stats/', 
         CandidateViewSet.as_view({'get': 'dashboard_stats'}), 
         name='candidate-dashboard-stats'),
    
    # Email-specific endpoints
    path('api/candidates/<int:candidate_pk>/emails/<int:pk>/mark-read/', 
         CandidateEmailViewSet.as_view({'post': 'mark_read'}), 
         name='candidate-email-mark-read'),
    
    path('api/candidates/<int:candidate_pk>/emails/<int:pk>/mark-unread/', 
         CandidateEmailViewSet.as_view({'post': 'mark_unread'}), 
         name='candidate-email-mark-unread'),
    
    # Attachment-specific endpoints
    path('api/candidates/<int:candidate_pk>/attachments/<int:pk>/set-primary-cv/', 
         EmailAttachmentViewSet.as_view({'post': 'set_primary_cv'}), 
         name='candidate-attachment-set-primary-cv'),
    
    path('api/candidates/<int:candidate_pk>/attachments/<int:pk>/toggle-visibility/', 
         EmailAttachmentViewSet.as_view({'post': 'toggle_visibility'}), 
         name='candidate-attachment-toggle-visibility'),
    
    path('api/candidates/<int:candidate_pk>/attachments/by-type/', 
         EmailAttachmentViewSet.as_view({'get': 'by_type'}), 
         name='candidate-attachments-by-type'),
    
    # MPR application-specific endpoints
    path('api/candidates/<int:candidate_pk>/mpr-applications/<int:pk>/update-stage/', 
         CandidateMPRViewSet.as_view({'post': 'update_stage'}), 
         name='candidate-mpr-update-stage'),
    
    path('api/candidates/<int:candidate_pk>/mpr-applications/<int:pk>/set-primary-cv/', 
         CandidateMPRViewSet.as_view({'post': 'set_primary_cv'}), 
         name='candidate-mpr-set-primary-cv'),
]

# API endpoints summary for documentation
"""
Candidate API Endpoints:

Main Resources:
- GET/POST /api/candidates/ - List/Create candidates
- GET/PUT/PATCH/DELETE /api/candidates/{id}/ - Retrieve/Update/Delete candidate
- GET /api/candidates/dashboard-stats/ - Dashboard statistics

Candidate Actions:
- POST /api/candidates/{id}/update-status/ - Update hiring status
- POST /api/candidates/{id}/calculate-scores/ - Recalculate scores
- POST /api/candidates/{id}/update-skill-matching/ - Update skill matching
- GET /api/candidates/{id}/timeline/ - Get candidate timeline

Email Management:
- GET/POST /api/candidates/{candidate_id}/emails/ - List/Create emails
- GET/PUT/PATCH/DELETE /api/candidates/{candidate_id}/emails/{id}/ - Manage email
- POST /api/candidates/{candidate_id}/emails/{id}/mark-read/ - Mark as read
- POST /api/candidates/{candidate_id}/emails/{id}/mark-unread/ - Mark as unread

Attachment Management:
- GET/POST /api/candidates/{candidate_id}/attachments/ - List/Upload attachments
- GET/PUT/PATCH/DELETE /api/candidates/{candidate_id}/attachments/{id}/ - Manage attachment
- POST /api/candidates/{candidate_id}/attachments/{id}/set-primary-cv/ - Set as primary CV
- POST /api/candidates/{candidate_id}/attachments/{id}/toggle-visibility/ - Toggle visibility
- GET /api/candidates/{candidate_id}/attachments/by-type/ - Group by type

Email Attachments:
- GET/POST /api/candidates/{candidate_id}/emails/{email_id}/attachments/ - Email attachments
- GET/PUT/PATCH/DELETE /api/candidates/{candidate_id}/emails/{email_id}/attachments/{id}/ - Manage

MPR Applications:
- GET/POST /api/candidates/{candidate_id}/mpr-applications/ - List/Create applications
- GET/PUT/PATCH/DELETE /api/candidates/{candidate_id}/mpr-applications/{id}/ - Manage application
- POST /api/candidates/{candidate_id}/mpr-applications/{id}/update-stage/ - Update stage
- POST /api/candidates/{candidate_id}/mpr-applications/{id}/set-primary-cv/ - Set primary CV

Filter Parameters:
- search: Text search across multiple fields
- hiring_status, hiring_status__in: Filter by hiring status
- overall_score__gte, overall_score__lte: Filter by score range
- skill_match_percentage__gte, skill_match_percentage__lte: Filter by skill match
- experience_years__gte, experience_years__lte: Filter by experience
- applied_after, applied_before, applied_date_range: Filter by application date
- location__icontains, current_company__icontains: Filter by location/company
- has_interviews, has_active_interviews, has_completed_interviews: Filter by interviews
- has_attachments, has_primary_cv: Filter by attachments
- applied_to_mpr, application_stage: Filter by MPR applications

Example Usage:
GET /api/candidates/?hiring_status=portfolio_review&overall_score__gte=4.0
GET /api/candidates/?search=john&has_active_interviews=true
GET /api/candidates/123/emails/?email_type=interview_invitation
GET /api/candidates/123/attachments/?file_type=cv&is_primary_cv=true
"""