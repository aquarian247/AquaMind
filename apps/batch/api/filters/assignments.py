"""
Batch container assignment filters.

These filters provide advanced filtering for batch container assignment endpoints.
"""
import django_filters as filters
from django_filters import rest_framework as rest_filters
from apps.batch.models import BatchContainerAssignment


class BatchContainerAssignmentFilter(rest_filters.FilterSet):
    """
    Advanced filter class for BatchContainerAssignment model.

    Provides comprehensive filtering options including date ranges,
    biomass ranges, and container relationships.
    """

    # Date range filters
    assignment_date_after = filters.DateFilter(field_name='assignment_date', lookup_expr='gte')
    assignment_date_before = filters.DateFilter(field_name='assignment_date', lookup_expr='lte')

    # Biomass range filters
    biomass_min = filters.NumberFilter(field_name='biomass_kg', lookup_expr='gte')
    biomass_max = filters.NumberFilter(field_name='biomass_kg', lookup_expr='lte')

    # Population range filters
    population_min = filters.NumberFilter(field_name='population_count', lookup_expr='gte')
    population_max = filters.NumberFilter(field_name='population_count', lookup_expr='lte')

    # Container relationship filters
    container_name = filters.CharFilter(
        field_name='container__name',
        lookup_expr='icontains'
    )
    container_type = filters.CharFilter(
        field_name='container__container_type__category',
        lookup_expr='iexact'
    )

    # Batch relationship filters
    batch_number = filters.CharFilter(
        field_name='batch__batch_number',
        lookup_expr='icontains'
    )
    species = filters.NumberFilter(field_name='batch__species')
    lifecycle_stage = filters.NumberFilter(field_name='batch__lifecycle_stage')

    class Meta:
        model = BatchContainerAssignment
        fields = {
            # Basic fields with __in support for foreign keys
            'batch': ['exact', 'in'],
            'container': ['exact', 'in'],
            'is_active': ['exact'],
            'assignment_date': ['exact']
        }
