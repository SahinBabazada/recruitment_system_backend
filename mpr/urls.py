# mpr/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    JobViewSet, OrganizationalUnitViewSet, LocationViewSet,
    EmploymentTypeViewSet, HiringReasonViewSet, EmployeeViewSet,
    TechnicalSkillViewSet, LanguageViewSet, CompetencyViewSet,
    ContractDurationViewSet, MPRViewSet
)

router = DefaultRouter()
router.register(r'jobs', JobViewSet, basename='job')
router.register(r'organizational-units', OrganizationalUnitViewSet, basename='organizational-unit')
router.register(r'locations', LocationViewSet, basename='location')
router.register(r'employment-types', EmploymentTypeViewSet, basename='employment-type')
router.register(r'hiring-reasons', HiringReasonViewSet, basename='hiring-reason')
router.register(r'employees', EmployeeViewSet, basename='employee')
router.register(r'technical-skills', TechnicalSkillViewSet, basename='technical-skill')
router.register(r'languages', LanguageViewSet, basename='language')
router.register(r'competencies', CompetencyViewSet, basename='competency')
router.register(r'contract-durations', ContractDurationViewSet, basename='contract-duration')
router.register(r'mprs', MPRViewSet, basename='mpr')

urlpatterns = [
    path('api/', include(router.urls)),
]