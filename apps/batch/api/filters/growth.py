"""
Growth sample filters.

These filters provide advanced filtering for growth sample endpoints.
"""
import django_filters as filters
from django_filters import rest_framework as rest_filters
from apps.batch.models import GrowthSample


class GrowthSampleFilter(rest_filters.FilterSet):
    """
    Advanced filter class for GrowthSample model.

    Provides comprehensive filtering options for growth sample tracking.
    """

    # Date range filters
    sample_date_after = filters.DateFilter(field_name='sample_date', lookup_expr='gte')
    sample_date_before = filters.DateFilter(field_name='sample_date', lookup_expr='lte')

    # Weight range filters
    avg_weight_min = filters.NumberFilter(field_name='avg_weight_g', lookup_expr='gte')
    avg_weight_max = filters.NumberFilter(field_name='avg_weight_g', lookup_expr='lte')

    # Length range filters
    avg_length_min = filters.NumberFilter(field_name='avg_length_cm', lookup_expr='gte')
    avg_length_max = filters.NumberFilter(field_name='avg_length_cm', lookup_expr='lte')

    # Sample size range filters
    sample_size_min = filters.NumberFilter(field_name='sample_size', lookup_expr='gte')
    sample_size_max = filters.NumberFilter(field_name='sample_size', lookup_expr='lte')

    # Condition factor range filters
    condition_factor_min = filters.NumberFilter(field_name='condition_factor', lookup_expr='gte')
    condition_factor_max = filters.NumberFilter(field_name='condition_factor', lookup_expr='lte')

    # Batch relationship filters
    batch_number = filters.CharFilter(
        field_name='assignment__batch__batch_number',
        lookup_expr='icontains'
    )
    container_name = filters.CharFilter(
        field_name='assignment__container__name',
        lookup_expr='icontains'
    )

    class Meta:
        model = GrowthSample
        fields = [
            'assignment__batch',
            'sample_date',
            'sample_date_after',
            'sample_date_before',
            'avg_weight_min',
            'avg_weight_max',
            'avg_length_min',
            'avg_length_max',
            'sample_size_min',
            'sample_size_max',
            'condition_factor_min',
            'condition_factor_max',
            'batch_number',
            'container_name',
        ]
