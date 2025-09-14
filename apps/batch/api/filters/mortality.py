"""
Mortality event filters.

These filters provide advanced filtering for mortality event endpoints.
"""
import django_filters as filters
from django_filters import rest_framework as rest_filters
from apps.batch.models import MortalityEvent


class MortalityEventFilter(rest_filters.FilterSet):
    """
    Advanced filter class for MortalityEvent model.

    Provides comprehensive filtering options for mortality tracking.
    """

    # Date range filters
    event_date_after = filters.DateFilter(field_name='event_date', lookup_expr='gte')
    event_date_before = filters.DateFilter(field_name='event_date', lookup_expr='lte')

    # Count range filters
    count_min = filters.NumberFilter(field_name='count', lookup_expr='gte')
    count_max = filters.NumberFilter(field_name='count', lookup_expr='lte')

    # Biomass range filters
    biomass_min = filters.NumberFilter(field_name='biomass_kg', lookup_expr='gte')
    biomass_max = filters.NumberFilter(field_name='biomass_kg', lookup_expr='lte')

    # Cause filter
    cause_in = filters.MultipleChoiceFilter(
        field_name='cause',
        choices=MortalityEvent.MORTALITY_CAUSE_CHOICES,
        lookup_expr='in'
    )

    # Batch relationship filters
    batch_number = filters.CharFilter(
        field_name='batch__batch_number',
        lookup_expr='icontains'
    )

    class Meta:
        model = MortalityEvent
        fields = [
            'batch',
            'event_date',
            'cause',
            'event_date_after',
            'event_date_before',
            'count_min',
            'count_max',
            'biomass_min',
            'biomass_max',
            'cause_in',
            'batch_number',
        ]
