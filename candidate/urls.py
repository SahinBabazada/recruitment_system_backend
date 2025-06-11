# candidate/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter
from .views import (
    CandidateViewSet, CandidateWorkExperienceViewSet, CandidateEducationViewSet,
    CandidateProjectViewSet, CandidateReferenceViewSet, CandidateEmailConnectionViewSet,
    CandidateAttachmentViewSet, CandidateStatusUpdateViewSet, CandidateMPRViewSet,
    CandidateAttachmentsByTypeView, EmailAttachmentsView, UpdateMPRApplicationStageView,
    SetPrimaryCVView, SyncCandidateEmailsView, BulkUpdateCandidateStatusView
)

# Main router
router = DefaultRouter()
router.register(r'candidates', CandidateViewSet, basename='candidate')

# Nested routers for candidate sub-resources
candidates_router = NestedDefaultRouter(router, r'candidates', lookup='candidate')
candidates_router.register(r'work-experiences', CandidateWorkExperienceViewSet, basename='candidate-work-experiences')
candidates_router.register(r'education', CandidateEducationViewSet, basename='candidate-education')
candidates_router.register(r'projects', CandidateProjectViewSet, basename='candidate-projects')
candidates_router.register(r'references', CandidateReferenceViewSet, basename='candidate-references')
candidates_router.register(r'email-connections', CandidateEmailConnectionViewSet, basename='candidate-email-connections')
candidates_router.register(r'attachments', CandidateAttachmentViewSet, basename='candidate-attachments')
candidates_router.register(r'status-updates', CandidateStatusUpdateViewSet, basename='candidate-status-updates')
candidates_router.register(r'mpr-applications', CandidateMPRViewSet, basename='candidate-mpr-applications')

urlpatterns = [
    # API endpoints - the router handles /candidates/ and /candidates/stats/ etc.
    path('', include(router.urls)),
    path('', include(candidates_router.urls)),
    
    # Additional custom endpoints
    path('candidates/<int:candidate_pk>/attachments/by-type/', 
         CandidateAttachmentsByTypeView.as_view(), 
         name='candidate-attachments-by-type'),
    
    path('candidates/<int:candidate_pk>/emails/<int:email_pk>/attachments/', 
         EmailAttachmentsView.as_view(), 
         name='candidate-email-attachments'),
    
    path('candidates/<int:candidate_pk>/mpr-applications/<int:application_pk>/update-stage/', 
         UpdateMPRApplicationStageView.as_view(), 
         name='update-mpr-application-stage'),
    
    path('candidates/<int:candidate_pk>/mpr-applications/<int:application_pk>/set-primary-cv/', 
         SetPrimaryCVView.as_view(), 
         name='set-primary-cv'),
    
    # Utility endpoints
    path('candidates/sync-emails/', 
         SyncCandidateEmailsView.as_view(), 
         name='sync-candidate-emails'),
    
    path('candidates/bulk-update-status/', 
         BulkUpdateCandidateStatusView.as_view(), 
         name='bulk-update-candidate-status'),
]