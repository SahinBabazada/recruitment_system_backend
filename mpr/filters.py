# mpr/filters.py
import django_filters
from django.db.models import Q
from .models import MPR, OrganizationalUnit, Location, EmploymentType, HiringReason


class MPRFilter(django_filters.FilterSet):
    """Filter class for MPR queries"""
    
    # Status filters
    status = django_filters.MultipleChoiceFilter(
        choices=MPR.STATUS_CHOICES,
        method='filter_status'
    )
    
    # Priority filters
    priority = django_filters.MultipleChoiceFilter(
        choices=MPR.PRIORITY_CHOICES
    )
    
    # Department filters
    department = django_filters.ModelMultipleChoiceFilter(
        queryset=OrganizationalUnit.objects.filter(type='department', is_active=True)
    )
    
    # Location filters
    location = django_filters.ModelMultipleChoiceFilter(
        queryset=Location.objects.filter(is_active=True)
    )
    
    # Employment type filters
    employment_type = django_filters.ModelMultipleChoiceFilter(
        queryset=EmploymentType.objects.filter(is_active=True)
    )
    
    # Hiring reason filters
    hiring_reason = django_filters.ModelMultipleChoiceFilter(
        queryset=HiringReason.objects.filter(is_active=True)
    )
    
    # Date filters
    created_at = django_filters.DateFromToRangeFilter()
    desired_start_date = django_filters.DateFromToRangeFilter()
    
    # User filters
    created_by = django_filters.CharFilter(
        field_name='created_by__username',
        lookup_expr='icontains'
    )
    
    recruiter = django_filters.CharFilter(
        field_name='recruiter__username',
        lookup_expr='icontains'
    )
    
    # Custom filters
    my_mprs = django_filters.BooleanFilter(
        method='filter_my_mprs',
        label='My MPRs only'
    )
    
    pending_approval = django_filters.BooleanFilter(
        method='filter_pending_approval',
        label='Pending my approval'
    )
    
    assigned_to_me = django_filters.BooleanFilter(
        method='filter_assigned_to_me',
        label='Assigned to me as recruiter'
    )
    
    urgent_only = django_filters.BooleanFilter(
        method='filter_urgent_only',
        label='Urgent and high priority only'
    )

    class Meta:
        model = MPR
        fields = {
            'mpr_number': ['exact', 'icontains'],
            'job_title__title': ['icontains'],
            'business_justification': ['icontains'],
        }

    def filter_status(self, queryset, name, value):
        """Filter by multiple status values"""
        if value:
            return queryset.filter(status__in=value)
        return queryset

    def filter_my_mprs(self, queryset, name, value):
        """Filter to show only user's own MPRs"""
        if value and self.request and self.request.user.is_authenticated:
            return queryset.filter(created_by=self.request.user)
        return queryset

    def filter_pending_approval(self, queryset, name, value):
        """Filter MPRs pending approval (if user can approve)"""
        if value and self.request and self.request.user.is_authenticated:
            user = self.request.user
            if hasattr(user, 'has_permission') and user.has_permission('mpr:approve'):
                return queryset.filter(status='pending')
        return queryset

    def filter_assigned_to_me(self, queryset, name, value):
        """Filter MPRs where user is assigned as recruiter"""
        if value and self.request and self.request.user.is_authenticated:
            return queryset.filter(recruiter=self.request.user)
        return queryset

    def filter_urgent_only(self, queryset, name, value):
        """Filter to show only urgent and high priority MPRs"""
        if value:
            return queryset.filter(priority__in=['urgent', 'high'])
        return queryset