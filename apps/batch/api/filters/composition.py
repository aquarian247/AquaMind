"""
Batch composition filters.

These filters provide advanced filtering for batch composition endpoints.
"""
import django_filters as filters
from django_filters import rest_framework as rest_filters
from apps.batch.models import BatchComposition


class BatchCompositionFilter(rest_filters.FilterSet):
    """
    Advanced filter class for BatchComposition model.

    Provides comprehensive filtering options for batch composition tracking.
    """

    # Population range filters
    population_min = filters.NumberFilter(field_name='population_count', lookup_expr='gte')
    population_max = filters.NumberFilter(field_name='population_count', lookup_expr='lte')

    # Biomass range filters
    biomass_min = filters.NumberFilter(field_name='biomass_kg', lookup_expr='gte')
    biomass_max = filters.NumberFilter(field_name='biomass_kg', lookup_expr='lte')

    # Percentage range filters
    percentage_min = filters.NumberFilter(field_name='percentage', lookup_expr='gte')
    percentage_max = filters.NumberFilter(field_name='percentage', lookup_expr='lte')

    # Batch relationship filters
    mixed_batch_number = filters.CharFilter(
        field_name='mixed_batch__batch_number',
        lookup_expr='icontains'
    )
    source_batch_number = filters.CharFilter(
        field_name='source_batch__batch_number',
        lookup_expr='icontains'
    )

    class Meta:
        model = BatchComposition
        fields = [
            'mixed_batch',
            'source_batch',
            'population_min',
            'population_max',
            'biomass_min',
            'biomass_max',
            'percentage_min',
            'percentage_max',
            'mixed_batch_number',
            'source_batch_number',
        ]
