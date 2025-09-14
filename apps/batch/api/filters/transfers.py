"""
Batch transfer filters.

These filters provide advanced filtering for batch transfer endpoints.
"""
import django_filters as filters
from django_filters import rest_framework as rest_filters
from apps.batch.models import BatchTransfer


class BatchTransferFilter(rest_filters.FilterSet):
    """
    Advanced filter class for BatchTransfer model.

    Provides comprehensive filtering options for transfer tracking.
    """

    # Date range filters
    transfer_date_after = filters.DateFilter(field_name='transfer_date', lookup_expr='gte')
    transfer_date_before = filters.DateFilter(field_name='transfer_date', lookup_expr='lte')

    # Population range filters
    population_min = filters.NumberFilter(field_name='population_count', lookup_expr='gte')
    population_max = filters.NumberFilter(field_name='population_count', lookup_expr='lte')

    # Biomass range filters
    biomass_min = filters.NumberFilter(field_name='biomass_kg', lookup_expr='gte')
    biomass_max = filters.NumberFilter(field_name='biomass_kg', lookup_expr='lte')

    # Transfer type filter
    transfer_type_in = filters.MultipleChoiceFilter(
        field_name='transfer_type',
        choices=BatchTransfer.TRANSFER_TYPE_CHOICES,
        lookup_expr='in'
    )

    # Batch relationship filters
    source_batch_number = filters.CharFilter(
        field_name='source_batch__batch_number',
        lookup_expr='icontains'
    )
    destination_batch_number = filters.CharFilter(
        field_name='destination_batch__batch_number',
        lookup_expr='icontains'
    )

    class Meta:
        model = BatchTransfer
        fields = [
            'source_batch',
            'destination_batch',
            'transfer_type',
            'source_lifecycle_stage',
            'destination_lifecycle_stage',
            'source_assignment',
            'destination_assignment',
            'transfer_date_after',
            'transfer_date_before',
            'population_min',
            'population_max',
            'biomass_min',
            'biomass_max',
            'transfer_type_in',
            'source_batch_number',
            'destination_batch_number',
        ]
