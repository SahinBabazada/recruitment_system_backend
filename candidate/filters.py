# candidate/filters.py
import django_filters
from django.db import models
from django.contrib.auth import get_user_model
from .models import Candidate, CandidateMPR

User = get_user_model()


class CandidateFilter(django_filters.FilterSet):
    """Filter set for Candidate model"""
    
    # Text search across multiple fields
    search = django_filters.CharFilter(method='filter_search', label='Search')
    
    # Status filters
    hiring_status = django_filters.ChoiceFilter(
        choices=Candidate.HIRING_STATUS_CHOICES,
        label='Hiring Status'
    )
    hiring_status__in = django_filters.MultipleChoiceFilter(
        field_name='hiring_status',
        choices=Candidate.HIRING_STATUS_CHOICES,
        label='Hiring Status (Multiple)'
    )
    
    # Score filters
    overall_score__gte = django_filters.NumberFilter(
        field_name='overall_score',
        lookup_expr='gte',
        label='Overall Score (Min)'
    )
    overall_score__lte = django_filters.NumberFilter(
        field_name='overall_score',
        lookup_expr='lte',
        label='Overall Score (Max)'
    )
    has_score = django_filters.BooleanFilter(
        method='filter_has_score',
        label='Has Overall Score'
    )
    
    # Skill matching filters
    skill_match_percentage__gte = django_filters.NumberFilter(
        field_name='skill_match_percentage',
        lookup_expr='gte',
        label='Skill Match % (Min)'
    )
    skill_match_percentage__lte = django_filters.NumberFilter(
        field_name='skill_match_percentage',
        lookup_expr='lte',
        label='Skill Match % (Max)'
    )
    
    # Experience filters
    experience_years__gte = django_filters.NumberFilter(
        field_name='experience_years',
        lookup_expr='gte',
        label='Experience Years (Min)'
    )
    experience_years__lte = django_filters.NumberFilter(
        field_name='experience_years',
        lookup_expr='lte',
        label='Experience Years (Max)'
    )
    
    # Date filters
    applied_after = django_filters.DateFilter(
        field_name='applied_at',
        lookup_expr='gte',
        label='Applied After'
    )
    applied_before = django_filters.DateFilter(
        field_name='applied_at',
        lookup_expr='lte',
        label='Applied Before'
    )
    applied_date_range = django_filters.DateFromToRangeFilter(
        field_name='applied_at',
        label='Applied Date Range'
    )
    
    # Location and company filters
    location__icontains = django_filters.CharFilter(
        field_name='location',
        lookup_expr='icontains',
        label='Location Contains'
    )
    current_company__icontains = django_filters.CharFilter(
        field_name='current_company',
        lookup_expr='icontains',
        label='Current Company Contains'
    )
    current_position__icontains = django_filters.CharFilter(
        field_name='current_position',
        lookup_expr='icontains',
        label='Current Position Contains'
    )
    
    # Professional skills filter
    professional_skills__contains = django_filters.CharFilter(
        method='filter_professional_skills',
        label='Has Professional Skill'
    )
    
    # Technical skills filter
    technical_skills__contains = django_filters.CharFilter(
        method='filter_technical_skills',
        label='Has Technical Skill'
    )
    
    # Languages filter
    languages__contains = django_filters.CharFilter(
        method='filter_languages',
        label='Speaks Language'
    )
    
    # Nationality filter
    nationality = django_filters.CharFilter(
        field_name='nationality',
        lookup_expr='iexact',
        label='Nationality'
    )
    
    # Relationship filters
    has_interviews = django_filters.BooleanFilter(
        method='filter_has_interviews',
        label='Has Interviews'
    )
    has_active_interviews = django_filters.BooleanFilter(
        method='filter_has_active_interviews',
        label='Has Active Interviews'
    )
    has_completed_interviews = django_filters.BooleanFilter(
        method='filter_has_completed_interviews',
        label='Has Completed Interviews'
    )
    has_attachments = django_filters.BooleanFilter(
        method='filter_has_attachments',
        label='Has Attachments'
    )
    has_primary_cv = django_filters.BooleanFilter(
        method='filter_has_primary_cv',
        label='Has Primary CV'
    )
    has_work_experience = django_filters.BooleanFilter(
        method='filter_has_work_experience',
        label='Has Work Experience'
    )
    has_education = django_filters.BooleanFilter(
        method='filter_has_education',
        label='Has Education History'
    )
    has_projects = django_filters.BooleanFilter(
        method='filter_has_projects',
        label='Has Projects'
    )
    
    # MPR application filters
    applied_to_mpr = django_filters.NumberFilter(
        field_name='mpr_applications__mpr',
        label='Applied to MPR ID'
    )
    application_stage = django_filters.ChoiceFilter(
        field_name='mpr_applications__application_stage',
        choices=CandidateMPR._meta.get_field('application_stage').choices,
        label='Application Stage'
    )
    
    # Salary filters
    salary_expectation__gte = django_filters.NumberFilter(
        field_name='salary_expectation',
        lookup_expr='gte',
        label='Salary Expectation (Min)'
    )
    salary_expectation__lte = django_filters.NumberFilter(
        field_name='salary_expectation',
        lookup_expr='lte',
        label='Salary Expectation (Max)'
    )
    salary_currency = django_filters.CharFilter(
        field_name='salary_currency',
        lookup_expr='iexact',
        label='Salary Currency'
    )
    
    # Availability filters
    available_from = django_filters.DateFilter(
        field_name='availability_date',
        lookup_expr='lte',
        label='Available From (Before)'
    )
    available_until = django_filters.DateFilter(
        field_name='availability_date',
        lookup_expr='gte',
        label='Available Until (After)'
    )
    
    # Notice period filter
    notice_period_days__lte = django_filters.NumberFilter(
        field_name='notice_period_days',
        lookup_expr='lte',
        label='Notice Period (Max Days)'
    )
    
    class Meta:
        model = Candidate
        fields = []
    
    def filter_search(self, queryset, name, value):
        """Search across multiple fields"""
        if not value:
            return queryset
        
        search_query = models.Q(name__icontains=value) | \
                      models.Q(email__icontains=value) | \
                      models.Q(phone__icontains=value) | \
                      models.Q(current_position__icontains=value) | \
                      models.Q(current_company__icontains=value) | \
                      models.Q(location__icontains=value)
        
        return queryset.filter(search_query).distinct()
    
    def filter_has_score(self, queryset, name, value):
        """Filter candidates with or without overall score"""
        if value is True:
            return queryset.filter(overall_score__isnull=False)
        elif value is False:
            return queryset.filter(overall_score__isnull=True)
        return queryset
    
    def filter_professional_skills(self, queryset, name, value):
        """Filter by professional skills"""
        if not value:
            return queryset
        return queryset.filter(professional_skills__icontains=value)
    
    def filter_technical_skills(self, queryset, name, value):
        """Filter by technical skills"""
        if not value:
            return queryset
        return queryset.filter(technical_skills__icontains=value)
    
    def filter_languages(self, queryset, name, value):
        """Filter by languages"""
        if not value:
            return queryset
        return queryset.filter(languages__icontains=value)
    
    def filter_has_interviews(self, queryset, name, value):
        """Filter candidates with or without interviews"""
        if value is True:
            return queryset.filter(interviews__isnull=False).distinct()
        elif value is False:
            return queryset.filter(interviews__isnull=True)
        return queryset
    
    def filter_has_active_interviews(self, queryset, name, value):
        """Filter candidates with active interviews"""
        if value is True:
            return queryset.filter(
                interviews__status__in=['scheduled', 'confirmed', 'in_progress']
            ).distinct()
        elif value is False:
            return queryset.exclude(
                interviews__status__in=['scheduled', 'confirmed', 'in_progress']
            )
        return queryset
    
    def filter_has_completed_interviews(self, queryset, name, value):
        """Filter candidates with completed interviews"""
        if value is True:
            return queryset.filter(interviews__status='completed').distinct()
        elif value is False:
            return queryset.exclude(interviews__status='completed')
        return queryset
    
    def filter_has_attachments(self, queryset, name, value):
        """Filter candidates with or without attachments"""
        if value is True:
            return queryset.filter(attachments__isnull=False).distinct()
        elif value is False:
            return queryset.filter(attachments__isnull=True)
        return queryset
    
    def filter_has_primary_cv(self, queryset, name, value):
        """Filter candidates with or without primary CV"""
        if value is True:
            return queryset.filter(attachments__is_primary_cv=True).distinct()
        elif value is False:
            return queryset.exclude(attachments__is_primary_cv=True)
        return queryset
    
    def filter_has_work_experience(self, queryset, name, value):
        """Filter candidates with or without work experience"""
        if value is True:
            return queryset.filter(work_experiences__isnull=False).distinct()
        elif value is False:
            return queryset.filter(work_experiences__isnull=True)
        return queryset
    
    def filter_has_education(self, queryset, name, value):
        """Filter candidates with or without education history"""
        if value is True:
            return queryset.filter(education_history__isnull=False).distinct()
        elif value is False:
            return queryset.filter(education_history__isnull=True)
        return queryset
    
    def filter_has_projects(self, queryset, name, value):
        """Filter candidates with or without projects"""
        if value is True:
            return queryset.filter(projects__isnull=False).distinct()
        elif value is False:
            return queryset.filter(projects__isnull=True)
        return queryset


class CandidateMPRFilter(django_filters.FilterSet):
    """Filter set for CandidateMPR model"""
    
    # Application stage filters
    application_stage = django_filters.ChoiceFilter(
        choices=CandidateMPR._meta.get_field('application_stage').choices,
        label='Application Stage'
    )
    application_stage__in = django_filters.MultipleChoiceFilter(
        field_name='application_stage',
        choices=CandidateMPR._meta.get_field('application_stage').choices,
        label='Application Stage (Multiple)'
    )
    
    # Date filters
    applied_after = django_filters.DateFilter(
        field_name='applied_at',
        lookup_expr='gte',
        label='Applied After'
    )
    applied_before = django_filters.DateFilter(
        field_name='applied_at',
        lookup_expr='lte',
        label='Applied Before'
    )
    
    # MPR filters
    mpr_number = django_filters.CharFilter(
        field_name='mpr__mpr_number',
        lookup_expr='icontains',
        label='MPR Number'
    )
    job_title = django_filters.CharFilter(
        field_name='mpr__job_title__title',
        lookup_expr='icontains',
        label='Job Title'
    )
    department = django_filters.CharFilter(
        field_name='mpr__department__name',
        lookup_expr='icontains',
        label='Department'
    )
    
    # Primary CV filter
    has_primary_cv = django_filters.BooleanFilter(
        method='filter_has_primary_cv',
        label='Has Primary CV'
    )
    
    # Updated by filter
    updated_by = django_filters.ModelChoiceFilter(
        queryset=User.objects.none(),  # Will be set in __init__
        label='Updated By'
    )
    
    class Meta:
        model = CandidateMPR
        fields = []
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set the queryset for updated_by filter
        self.filters['updated_by'].queryset = User.objects.filter(
            updated_candidate_mprs__isnull=False
        ).distinct()
    
    def filter_has_primary_cv(self, queryset, name, value):
        """Filter applications with or without primary CV"""
        if value is True:
            return queryset.filter(primary_cv__isnull=False)
        elif value is False:
            return queryset.filter(primary_cv__isnull=True)
        return queryset