"""
Batch-specific filters.

These filters provide advanced filtering capabilities for batch-related endpoints.
"""
import django_filters as filters
from django_filters import rest_framework as rest_filters
from apps.batch.models import Batch


class BatchFilter(rest_filters.FilterSet):
    """
    Advanced filter class for Batch model.

    Provides comprehensive filtering options for batch endpoints including
    status, type, species, lifecycle stage, and date range filtering.
    """

    # Date range filters
    start_date_after = filters.DateFilter(field_name='start_date', lookup_expr='gte')
    start_date_before = filters.DateFilter(field_name='start_date', lookup_expr='lte')
    end_date_after = filters.DateFilter(field_name='expected_end_date', lookup_expr='gte')
    end_date_before = filters.DateFilter(field_name='expected_end_date', lookup_expr='lte')

    # Biomass range filters
    biomass_min = filters.NumberFilter(field_name='biomass_kg', lookup_expr='gte')
    biomass_max = filters.NumberFilter(field_name='biomass_kg', lookup_expr='lte')

    # Population range filters
    population_min = filters.NumberFilter(field_name='population_count', lookup_expr='gte')
    population_max = filters.NumberFilter(field_name='population_count', lookup_expr='lte')

    # Status choices filter
    status_in = filters.MultipleChoiceFilter(
        field_name='status',
        choices=Batch.BATCH_STATUS_CHOICES,
        lookup_expr='in'
    )

    # Batch type choices filter
    batch_type_in = filters.MultipleChoiceFilter(
        field_name='batch_type',
        choices=Batch.BATCH_TYPE_CHOICES,
        lookup_expr='in'
    )

    class Meta:
        model = Batch
        fields = [
            # Basic fields
            'batch_number',
            'species',
            'lifecycle_stage',
            'status',
            'batch_type',

            # Date filters
            'start_date_after',
            'start_date_before',
            'end_date_after',
            'end_date_before',

            # Biomass and population filters
            'biomass_min',
            'biomass_max',
            'population_min',
            'population_max',

            # Multiple choice filters
            'status_in',
            'batch_type_in',
        ]
