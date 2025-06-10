import django_filters
from django.db.models import Q
from .models import Candidate, CandidateEmail, EmailAttachment, CandidateMPR


class CandidateMPRFilter(django_filters.FilterSet):
    """Filter set for CandidateMPR model"""
    
    application_stage = django_filters.ChoiceFilter(
        choices=CandidateMPR._meta.get_field('application_stage').choices,
        label='Application Stage'
    )
    
    application_stage__in = django_filters.MultipleChoiceFilter(
        field_name='application_stage',
        choices=CandidateMPR._meta.get_field('application_stage').choices,
        label='Application Stage (Multiple)'
    )
    
    mpr_status = django_filters.CharFilter(
        field_name='mpr__status',
        label='MPR Status'
    )
    
    technical_fit_score__gte = django_filters.NumberFilter(
        field_name='technical_fit_score',
        lookup_expr='gte',
        label='Technical Fit Score (Min)'
    )
    technical_fit_score__lte = django_filters.NumberFilter(
        field_name='technical_fit_score',
        lookup_expr='lte',
        label='Technical Fit Score (Max)'
    )
    
    cultural_fit_score__gte = django_filters.NumberFilter(
        field_name='cultural_fit_score',
        lookup_expr='gte',
        label='Cultural Fit Score (Min)'
    )
    cultural_fit_score__lte = django_filters.NumberFilter(
        field_name='cultural_fit_score',
        lookup_expr='lte',
        label='Cultural Fit Score (Max)'
    )
    
    applied_after = django_filters.DateTimeFilter(
        field_name='applied_at',
        lookup_expr='gte',
        label='Applied After'
    )
    applied_before = django_filters.DateTimeFilter(
        field_name='applied_at',
        lookup_expr='lte',
        label='Applied Before'
    )
    
    has_primary_cv = django_filters.BooleanFilter(
        method='filter_has_primary_cv',
        label='Has Primary CV'
    )
    
    mpr_job_title__icontains = django_filters.CharFilter(
        field_name='mpr__job_title__title',
        lookup_expr='icontains',
        label='Job Title Contains'
    )
    
    mpr_department = django_filters.NumberFilter(
        field_name='mpr__department',
        label='MPR Department ID'
    )
    
    updated_by = django_filters.ModelChoiceFilter(
        field_name='updated_by',
        queryset=None,  # Will be set in __init__
        label='Updated By'
    )
    
    class Meta:
        model = CandidateMPR
        fields = []
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set the queryset for updated_by filter
        from django.contrib.auth.models import User
        self.filters['updated_by'].queryset = User.objects.filter(
            updated_candidate_mprs__isnull=False
        ).distinct()
    
    def filter_has_primary_cv(self, queryset, name, value):
        """Filter applications with or without primary CV"""
        if value is True:
            return queryset.filter(primary_cv__isnull=False)
        elif value is False:
            return queryset.filter(primary_cv__isnull=True)
        return querysetandidateFilter(django_filters.FilterSet):
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
    
    # Availability filter
    available_after = django_filters.DateFilter(
        field_name='availability_date',
        lookup_expr='gte',
        label='Available After'
    )
    available_before = django_filters.DateFilter(
        field_name='availability_date',
        lookup_expr='lte',
        label='Available Before'
    )
    
    class Meta:
        model = Candidate
        fields = []
    
    def filter_search(self, queryset, name, value):
        """Search across multiple fields"""
        if not value:
            return queryset
        
        return queryset.filter(
            Q(name__icontains=value) |
            Q(email__icontains=value) |
            Q(current_position__icontains=value) |
            Q(current_company__icontains=value) |
            Q(location__icontains=value) |
            Q(internal_notes__icontains=value)
        )
    
    def filter_has_score(self, queryset, name, value):
        """Filter candidates with or without overall score"""
        if value is True:
            return queryset.filter(overall_score__isnull=False)
        elif value is False:
            return queryset.filter(overall_score__isnull=True)
        return queryset
    
    def filter_professional_skills(self, queryset, name, value):
        """Filter by professional skills (JSON field)"""
        if not value:
            return queryset
        
        return queryset.filter(professional_skills__contains=[value])
    
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


class CandidateEmailFilter(django_filters.FilterSet):
    """Filter set for CandidateEmail model"""
    
    search = django_filters.CharFilter(method='filter_search', label='Search')
    
    email_type = django_filters.ChoiceFilter(
        choices=CandidateEmail._meta.get_field('email_type').choices,
        label='Email Type'
    )
    
    is_inbound = django_filters.BooleanFilter(label='Is Inbound')
    is_read = django_filters.BooleanFilter(label='Is Read')
    
    sent_after = django_filters.DateTimeFilter(
        field_name='sent_at',
        lookup_expr='gte',
        label='Sent After'
    )
    sent_before = django_filters.DateTimeFilter(
        field_name='sent_at',
        lookup_expr='lte',
        label='Sent Before'
    )
    
    has_attachments = django_filters.BooleanFilter(
        method='filter_has_attachments',
        label='Has Attachments'
    )
    
    from_email__icontains = django_filters.CharFilter(
        field_name='from_email',
        lookup_expr='icontains',
        label='From Email Contains'
    )
    
    class Meta:
        model = CandidateEmail
        fields = []
    
    def filter_search(self, queryset, name, value):
        """Search across email fields"""
        if not value:
            return queryset
        
        return queryset.filter(
            Q(subject__icontains=value) |
            Q(body__icontains=value) |
            Q(from_email__icontains=value) |
            Q(to_email__icontains=value)
        )
    
    def filter_has_attachments(self, queryset, name, value):
        """Filter emails with or without attachments"""
        if value is True:
            return queryset.filter(attachments__isnull=False).distinct()
        elif value is False:
            return queryset.filter(attachments__isnull=True)
        return queryset


class EmailAttachmentFilter(django_filters.FilterSet):
    """Filter set for EmailAttachment model"""
    
    search = django_filters.CharFilter(method='filter_search', label='Search')
    
    file_type = django_filters.ChoiceFilter(
        choices=EmailAttachment._meta.get_field('file_type').choices,
        label='File Type'
    )
    
    is_visible_to_line_manager = django_filters.BooleanFilter(
        label='Visible to Line Manager'
    )
    is_primary_cv = django_filters.BooleanFilter(label='Is Primary CV')
    is_processed = django_filters.BooleanFilter(label='Is Processed')
    
    file_size__gte = django_filters.NumberFilter(
        field_name='file_size',
        lookup_expr='gte',
        label='File Size (Min Bytes)'
    )
    file_size__lte = django_filters.NumberFilter(
        field_name='file_size',
        lookup_expr='lte',
        label='File Size (Max Bytes)'
    )
    
    uploaded_after = django_filters.DateTimeFilter(
        field_name='uploaded_at',
        lookup_expr='gte',
        label='Uploaded After'
    )
    uploaded_before = django_filters.DateTimeFilter(
        field_name='uploaded_at',
        lookup_expr='lte',
        label='Uploaded Before'
    )
    
    mime_type__icontains = django_filters.CharFilter(
        field_name='mime_type',
        lookup_expr='icontains',
        label='MIME Type Contains'
    )
    
    class Meta:
        model = EmailAttachment
        fields = []
    
    def filter_search(self, queryset, name, value):
        """Search across attachment fields"""
        if not value:
            return queryset
        
        return queryset.filter(
            Q(original_file_name__icontains=value) |
            Q(file_name__icontains=value) |
            Q(extracted_text__icontains=value)
        )