import django_filters
from django.db.models import Q, Count, F
from django.utils import timezone
from datetime import timedelta
from .models import Interview, InterviewParticipant, InterviewQuestion, InterviewRound


class InterviewFilter(django_filters.FilterSet):
    """Filter set for Interview model"""
    
    # Text search across multiple fields
    search = django_filters.CharFilter(method='filter_search', label='Search')
    
    # Status filters
    status = django_filters.ChoiceFilter(
        choices=Interview.STATUS_CHOICES,
        label='Interview Status'
    )
    status__in = django_filters.MultipleChoiceFilter(
        field_name='status',
        choices=Interview.STATUS_CHOICES,
        label='Interview Status (Multiple)'
    )
    
    # Date filters
    scheduled_date = django_filters.DateFilter(
        field_name='scheduled_date__date',
        label='Scheduled Date'
    )
    scheduled_after = django_filters.DateTimeFilter(
        field_name='scheduled_date',
        lookup_expr='gte',
        label='Scheduled After'
    )
    scheduled_before = django_filters.DateTimeFilter(
        field_name='scheduled_date',
        lookup_expr='lte',
        label='Scheduled Before'
    )
    scheduled_date_range = django_filters.DateFromToRangeFilter(
        field_name='scheduled_date__date',
        label='Scheduled Date Range'
    )
    
    # Time-based filters
    is_upcoming = django_filters.BooleanFilter(
        method='filter_is_upcoming',
        label='Is Upcoming'
    )
    is_overdue = django_filters.BooleanFilter(
        method='filter_is_overdue',
        label='Is Overdue'
    )
    is_today = django_filters.BooleanFilter(
        method='filter_is_today',
        label='Is Today'
    )
    is_this_week = django_filters.BooleanFilter(
        method='filter_is_this_week',
        label='Is This Week'
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
    
    # Recommendation filter
    recommendation = django_filters.ChoiceFilter(
        choices=Interview.RECOMMENDATION_CHOICES,
        label='Recommendation'
    )
    recommendation__in = django_filters.MultipleChoiceFilter(
        field_name='recommendation',
        choices=Interview.RECOMMENDATION_CHOICES,
        label='Recommendation (Multiple)'
    )
    
    # Interview round filters
    interview_round = django_filters.ModelChoiceFilter(
        queryset=InterviewRound.objects.filter(is_active=True),
        label='Interview Round'
    )
    interview_round__in = django_filters.ModelMultipleChoiceFilter(
        field_name='interview_round',
        queryset=InterviewRound.objects.filter(is_active=True),
        label='Interview Round (Multiple)'
    )
    
    # Candidate filters
    candidate = django_filters.NumberFilter(
        field_name='candidate',
        label='Candidate ID'
    )
    candidate_name__icontains = django_filters.CharFilter(
        field_name='candidate__name',
        lookup_expr='icontains',
        label='Candidate Name Contains'
    )
    candidate_email__icontains = django_filters.CharFilter(
        field_name='candidate__email',
        lookup_expr='icontains',
        label='Candidate Email Contains'
    )
    candidate_status = django_filters.CharFilter(
        field_name='candidate__hiring_status',
        label='Candidate Hiring Status'
    )
    
    # MPR filters
    mpr = django_filters.NumberFilter(
        field_name='mpr',
        label='MPR ID'
    )
    mpr_title__icontains = django_filters.CharFilter(
        field_name='mpr__job_title__title',
        lookup_expr='icontains',
        label='Job Title Contains'
    )
    mpr_number__icontains = django_filters.CharFilter(
        field_name='mpr__mpr_number',
        lookup_expr='icontains',
        label='MPR Number Contains'
    )
    mpr_status = django_filters.CharFilter(
        field_name='mpr__status',
        label='MPR Status'
    )
    mpr_department = django_filters.NumberFilter(
        field_name='mpr__department',
        label='MPR Department ID'
    )
    
    # Location filters
    location__icontains = django_filters.CharFilter(
        field_name='location',
        lookup_expr='icontains',
        label='Location Contains'
    )
    is_online = django_filters.BooleanFilter(
        method='filter_is_online',
        label='Is Online Interview'
    )
    
    # Duration filters
    duration_minutes__gte = django_filters.NumberFilter(
        field_name='duration_minutes',
        lookup_expr='gte',
        label='Duration (Min Minutes)'
    )
    duration_minutes__lte = django_filters.NumberFilter(
        field_name='duration_minutes',
        lookup_expr='lte',
        label='Duration (Max Minutes)'
    )
    
    # Participant filters
    has_participants = django_filters.BooleanFilter(
        method='filter_has_participants',
        label='Has Participants'
    )
    participant_user = django_filters.NumberFilter(
        field_name='participants__user',
        label='Participant User ID'
    )
    participant_role = django_filters.ChoiceFilter(
        field_name='participants__role',
        choices=InterviewParticipant.ROLE_CHOICES,
        label='Participant Role'
    )
    
    # Feedback filters
    has_feedback = django_filters.BooleanFilter(
        method='filter_has_feedback',
        label='Has Feedback'
    )
    has_complete_feedback = django_filters.BooleanFilter(
        method='filter_has_complete_feedback',
        label='Has Complete Feedback'
    )
    
    # Creation filters
    created_by = django_filters.NumberFilter(
        field_name='created_by',
        label='Created By User ID'
    )
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
        label='Created After'
    )
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
        label='Created Before'
    )
    
    class Meta:
        model = Interview  # FIXED: Changed from InterviewParticipant to Interview
        fields = []
    
    def filter_search(self, queryset, name, value):
        """Search across multiple fields"""
        if not value:
            return queryset
        
        return queryset.filter(
            Q(title__icontains=value) |
            Q(candidate__name__icontains=value) |
            Q(candidate__email__icontains=value) |
            Q(mpr__job_title__title__icontains=value) |
            Q(mpr__mpr_number__icontains=value) |
            Q(location__icontains=value) |
            Q(general_feedback__icontains=value) |
            Q(interviewer_notes__icontains=value)
        )
    
    def filter_is_upcoming(self, queryset, name, value):
        """Filter upcoming interviews"""
        if value is True:
            return queryset.filter(
                scheduled_date__gt=timezone.now(),
                status__in=['scheduled', 'confirmed']
            )
        elif value is False:
            return queryset.exclude(
                scheduled_date__gt=timezone.now(),
                status__in=['scheduled', 'confirmed']
            )
        return queryset
    
    def filter_is_overdue(self, queryset, name, value):
        """Filter overdue interviews"""
        if value is True:
            return queryset.filter(
                scheduled_date__lt=timezone.now(),
                status__in=['scheduled', 'confirmed']
            )
        elif value is False:
            return queryset.exclude(
                scheduled_date__lt=timezone.now(),
                status__in=['scheduled', 'confirmed']
            )
        return queryset
    
    def filter_is_today(self, queryset, name, value):
        """Filter interviews scheduled for today"""
        if value is True:
            today = timezone.now().date()
            return queryset.filter(scheduled_date__date=today)
        elif value is False:
            today = timezone.now().date()
            return queryset.exclude(scheduled_date__date=today)
        return queryset
    
    def filter_is_this_week(self, queryset, name, value):
        """Filter interviews scheduled for this week"""
        if value is True:
            today = timezone.now().date()
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)
            return queryset.filter(scheduled_date__date__range=[week_start, week_end])
        elif value is False:
            today = timezone.now().date()
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)
            return queryset.exclude(scheduled_date__date__range=[week_start, week_end])
        return queryset
    
    def filter_has_score(self, queryset, name, value):
        """Filter interviews with or without overall score"""
        if value is True:
            return queryset.filter(overall_score__isnull=False)
        elif value is False:
            return queryset.filter(overall_score__isnull=True)
        return queryset
    
    def filter_is_online(self, queryset, name, value):
        """Filter online interviews (those with meeting links)"""
        if value is True:
            return queryset.filter(meeting_link__isnull=False).exclude(meeting_link='')
        elif value is False:
            return queryset.filter(Q(meeting_link__isnull=True) | Q(meeting_link=''))
        return queryset
    
    def filter_has_participants(self, queryset, name, value):
        """Filter interviews with or without participants"""
        if value is True:
            return queryset.filter(participants__isnull=False).distinct()
        elif value is False:
            return queryset.filter(participants__isnull=True)
        return queryset
    
    def filter_has_feedback(self, queryset, name, value):
        """Filter interviews with feedback"""
        if value is True:
            return queryset.filter(
                Q(general_feedback__isnull=False) & ~Q(general_feedback='') |
                Q(participants__individual_feedback__isnull=False) & ~Q(participants__individual_feedback='')
            ).distinct()
        elif value is False:
            return queryset.filter(
                Q(general_feedback__isnull=True) | Q(general_feedback=''),
                Q(participants__individual_feedback__isnull=True) | Q(participants__individual_feedback='')
            )
        return queryset
    
    def filter_has_complete_feedback(self, queryset, name, value):
        """Filter interviews with complete feedback from all participants"""
        if value is True:
            # Interviews where all participants have provided feedback
            return queryset.filter(
                participants__individual_score__isnull=False
            ).annotate(
                total_participants=Count('participants'),
                participants_with_feedback=Count('participants__individual_score')
            ).filter(
                total_participants=F('participants_with_feedback')
            ).distinct()
        elif value is False:
            # Interviews where not all participants have provided feedback
            return queryset.exclude(
                participants__individual_score__isnull=False
            ).annotate(
                total_participants=Count('participants'),
                participants_with_feedback=Count('participants__individual_score')
            ).exclude(
                total_participants=F('participants_with_feedback')
            )
        return queryset


class InterviewParticipantFilter(django_filters.FilterSet):
    """Filter set for InterviewParticipant model"""
    
    role = django_filters.ChoiceFilter(
        choices=InterviewParticipant.ROLE_CHOICES,
        label='Participant Role'
    )
    role__in = django_filters.MultipleChoiceFilter(
        field_name='role',
        choices=InterviewParticipant.ROLE_CHOICES,
        label='Participant Role (Multiple)'
    )
    
    attended = django_filters.BooleanFilter(label='Attended')
    
    has_individual_score = django_filters.BooleanFilter(
        method='filter_has_individual_score',
        label='Has Individual Score'
    )
    
    individual_score__gte = django_filters.NumberFilter(
        field_name='individual_score',
        lookup_expr='gte',
        label='Individual Score (Min)'
    )
    individual_score__lte = django_filters.NumberFilter(
        field_name='individual_score',
        lookup_expr='lte',
        label='Individual Score (Max)'
    )
    
    individual_recommendation = django_filters.ChoiceFilter(
        choices=Interview.RECOMMENDATION_CHOICES,
        label='Individual Recommendation'
    )
    
    user = django_filters.NumberFilter(
        field_name='user',
        label='User ID'
    )
    user_name__icontains = django_filters.CharFilter(
        method='filter_user_name',
        label='User Name Contains'
    )
    
    send_calendar_invite = django_filters.BooleanFilter(label='Send Calendar Invite')
    send_reminders = django_filters.BooleanFilter(label='Send Reminders')
    
    class Meta:
        model = InterviewParticipant
        fields = []
    
    def filter_has_individual_score(self, queryset, name, value):
        """Filter participants with or without individual score"""
        if value is True:
            return queryset.filter(individual_score__isnull=False)
        elif value is False:
            return queryset.filter(individual_score__isnull=True)
        return queryset
    
    def filter_user_name(self, queryset, name, value):
        """Filter by user name"""
        if not value:
            return queryset
        
        return queryset.filter(
            Q(user__first_name__icontains=value) |
            Q(user__last_name__icontains=value) |
            Q(user__username__icontains=value)
        )


class InterviewQuestionFilter(django_filters.FilterSet):
    """Filter set for InterviewQuestion model"""
    
    search = django_filters.CharFilter(method='filter_search', label='Search')
    
    interview_round = django_filters.ModelChoiceFilter(
        queryset=InterviewRound.objects.filter(is_active=True),
        label='Interview Round'
    )
    
    question_type = django_filters.ChoiceFilter(
        choices=InterviewQuestion._meta.get_field('question_type').choices,
        label='Question Type'
    )
    question_type__in = django_filters.MultipleChoiceFilter(
        field_name='question_type',
        choices=InterviewQuestion._meta.get_field('question_type').choices,
        label='Question Type (Multiple)'
    )
    
    difficulty_level = django_filters.ChoiceFilter(
        choices=InterviewQuestion._meta.get_field('difficulty_level').choices,
        label='Difficulty Level'
    )
    difficulty_level__in = django_filters.MultipleChoiceFilter(
        field_name='difficulty_level',
        choices=InterviewQuestion._meta.get_field('difficulty_level').choices,
        label='Difficulty Level (Multiple)'
    )
    
    is_active = django_filters.BooleanFilter(label='Is Active')
    
    estimated_time_minutes__gte = django_filters.NumberFilter(
        field_name='estimated_time_minutes',
        lookup_expr='gte',
        label='Estimated Time (Min Minutes)'
    )
    estimated_time_minutes__lte = django_filters.NumberFilter(
        field_name='estimated_time_minutes',
        lookup_expr='lte',
        label='Estimated Time (Max Minutes)'
    )
    
    usage_count__gte = django_filters.NumberFilter(
        field_name='usage_count',
        lookup_expr='gte',
        label='Usage Count (Min)'
    )
    usage_count__lte = django_filters.NumberFilter(
        field_name='usage_count',
        lookup_expr='lte',
        label='Usage Count (Max)'
    )
    
    has_follow_up_questions = django_filters.BooleanFilter(
        method='filter_has_follow_up_questions',
        label='Has Follow-up Questions'
    )
    
    has_ideal_answer_points = django_filters.BooleanFilter(
        method='filter_has_ideal_answer_points',
        label='Has Ideal Answer Points'
    )
    
    created_by = django_filters.NumberFilter(
        field_name='created_by',
        label='Created By User ID'
    )
    
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
        label='Created After'
    )
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
        label='Created Before'
    )
    
    evaluation_criteria__contains = django_filters.CharFilter(
        method='filter_evaluation_criteria',
        label='Has Evaluation Criteria'
    )
    
    class Meta:
        model = InterviewQuestion
        fields = []
    
    def filter_search(self, queryset, name, value):
        """Search across question fields"""
        if not value:
            return queryset
        
        return queryset.filter(
            Q(question_text__icontains=value) |
            Q(follow_up_questions__icontains=value) |
            Q(ideal_answer_points__icontains=value)
        )
    
    def filter_has_follow_up_questions(self, queryset, name, value):
        """Filter questions with or without follow-up questions"""
        if value is True:
            return queryset.filter(follow_up_questions__isnull=False).exclude(follow_up_questions='')
        elif value is False:
            return queryset.filter(Q(follow_up_questions__isnull=True) | Q(follow_up_questions=''))
        return queryset
    
    def filter_has_ideal_answer_points(self, queryset, name, value):
        """Filter questions with or without ideal answer points"""
        if value is True:
            return queryset.filter(ideal_answer_points__isnull=False).exclude(ideal_answer_points='')
        elif value is False:
            return queryset.filter(Q(ideal_answer_points__isnull=True) | Q(ideal_answer_points=''))
        return queryset
    
    def filter_evaluation_criteria(self, queryset, name, value):
        """Filter by evaluation criteria (JSON field)"""
        if not value:
            return queryset
        
        return queryset.filter(evaluation_criteria__contains=[value])