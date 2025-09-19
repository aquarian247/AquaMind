"""
Feeding event filters.

These filters provide advanced filtering for feeding event endpoints.
"""
import django_filters as filters
from django_filters import rest_framework as rest_filters
from apps.inventory.models import FeedingEvent


class FeedingEventFilter(rest_filters.FilterSet):
    """
    Advanced filter class for FeedingEvent model.

    Provides comprehensive filtering options for feeding event tracking.
    """

    # Date range filters
    feeding_date_after = filters.DateFilter(field_name='feeding_date', lookup_expr='gte')
    feeding_date_before = filters.DateFilter(field_name='feeding_date', lookup_expr='lte')

    # Amount range filters
    amount_min = filters.NumberFilter(field_name='amount_kg', lookup_expr='gte')
    amount_max = filters.NumberFilter(field_name='amount_kg', lookup_expr='lte')

    # Method filter
    method_in = filters.MultipleChoiceFilter(
        field_name='method',
        choices=FeedingEvent.FEEDING_METHOD_CHOICES,
        lookup_expr='in'
    )

    # Batch relationship filters
    batch_number = filters.CharFilter(
        field_name='batch__batch_number',
        lookup_expr='icontains'
    )

    # Container relationship filters
    container_name = filters.CharFilter(
        field_name='container__name',
        lookup_expr='icontains'
    )

    # Feed relationship filters
    feed_name = filters.CharFilter(
        field_name='feed__name',
        lookup_expr='icontains'
    )

    class Meta:
        model = FeedingEvent
        fields = {
            # Basic fields with __in support for foreign keys
            'batch': ['exact', 'in'],
            'feed': ['exact', 'in'],
            'container': ['exact', 'in'],
            'feeding_date': ['exact'],
            'method': ['exact']
        }
