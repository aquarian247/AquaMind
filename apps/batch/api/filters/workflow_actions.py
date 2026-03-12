"""
Transfer action filters.

These filters provide advanced filtering for transfer action endpoints.
"""
import django_filters as filters
from django_filters import rest_framework as rest_filters
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from apps.batch.models import TransferAction
from apps.infrastructure.models import FreshwaterStation


class TransferActionFilter(rest_filters.FilterSet):
    """
    Advanced filter class for TransferAction model.

    Provides comprehensive filtering options for action tracking.
    """

    # Date range filters
    planned_date_after = filters.DateFilter(
        field_name='planned_date',
        lookup_expr='gte'
    )
    planned_date_before = filters.DateFilter(
        field_name='planned_date',
        lookup_expr='lte'
    )
    execution_date_after = filters.DateFilter(
        field_name='actual_execution_date',
        lookup_expr='gte'
    )
    execution_date_before = filters.DateFilter(
        field_name='actual_execution_date',
        lookup_expr='lte'
    )

    # Status filter
    status_in = filters.MultipleChoiceFilter(
        field_name='status',
        choices=TransferAction.STATUS_CHOICES,
        lookup_expr='in'
    )

    # Transfer method filter
    transfer_method_in = filters.MultipleChoiceFilter(
        field_name='transfer_method',
        choices=TransferAction.TRANSFER_METHOD_CHOICES,
        lookup_expr='in'
    )

    # Workflow filters
    workflow_number = filters.CharFilter(
        field_name='workflow__workflow_number',
        lookup_expr='icontains'
    )
    workflow_status = filters.CharFilter(
        field_name='workflow__status',
        lookup_expr='exact'
    )

    # Count range filters
    transferred_count_min = filters.NumberFilter(
        field_name='transferred_count',
        lookup_expr='gte'
    )
    transferred_count_max = filters.NumberFilter(
        field_name='transferred_count',
        lookup_expr='lte'
    )

    # Biomass range filters
    biomass_min = filters.NumberFilter(
        field_name='transferred_biomass_kg',
        lookup_expr='gte'
    )
    biomass_max = filters.NumberFilter(
        field_name='transferred_biomass_kg',
        lookup_expr='lte'
    )

    # Container filters
    source_container = filters.NumberFilter(
        field_name='source_assignment__container',
        lookup_expr='exact'
    )
    dest_container = filters.NumberFilter(
        field_name='dest_assignment__container',
        lookup_expr='exact'
    )
    station = filters.NumberFilter(method='filter_station')

    class Meta:
        model = TransferAction
        fields = [
            'workflow',
            'status',
            'source_assignment',
            'dest_assignment',
            'transfer_method',
            'executed_by',
            'planned_date_after',
            'planned_date_before',
            'execution_date_after',
            'execution_date_before',
            'status_in',
            'transfer_method_in',
            'workflow_number',
            'workflow_status',
            'transferred_count_min',
            'transferred_count_max',
            'biomass_min',
            'biomass_max',
            'source_container',
            'dest_container',
            'station',
        ]

    def filter_station(self, queryset, name, value):
        try:
            station_id = int(value)
        except (TypeError, ValueError):
            raise ValidationError({'station': 'Invalid freshwater station ID'})

        if not FreshwaterStation.objects.filter(id=station_id).exists():
            raise ValidationError({'station': 'Freshwater station not found'})

        return queryset.filter(
            Q(source_assignment__container__hall__freshwater_station_id=station_id)
            | Q(dest_assignment__container__hall__freshwater_station_id=station_id)
            | Q(dest_container__hall__freshwater_station_id=station_id)
        )
