"""
Species and lifecycle stage filters.

These filters provide advanced filtering for species and lifecycle stage endpoints.
"""
import django_filters as filters
from django_filters import rest_framework as rest_filters
from apps.batch.models import Species, LifeCycleStage


class SpeciesFilter(rest_filters.FilterSet):
    """
    Advanced filter class for Species model.

    Provides comprehensive filtering options for species management.
    """

    # Name filters with case-insensitive search
    name_contains = filters.CharFilter(field_name='name', lookup_expr='icontains')
    scientific_name_contains = filters.CharFilter(field_name='scientific_name', lookup_expr='icontains')

    # Description filter
    description_contains = filters.CharFilter(field_name='description', lookup_expr='icontains')

    class Meta:
        model = Species
        fields = [
            'name',
            'scientific_name',
            'name_contains',
            'scientific_name_contains',
            'description_contains',
        ]


class LifeCycleStageFilter(rest_filters.FilterSet):
    """
    Advanced filter class for LifeCycleStage model.

    Provides comprehensive filtering options for lifecycle stage management.
    """

    # Name filter
    name_contains = filters.CharFilter(field_name='name', lookup_expr='icontains')

    # Order range filters
    order_min = filters.NumberFilter(field_name='order', lookup_expr='gte')
    order_max = filters.NumberFilter(field_name='order', lookup_expr='lte')

    # Species relationship filter
    species_name = filters.CharFilter(
        field_name='species__name',
        lookup_expr='icontains'
    )

    class Meta:
        model = LifeCycleStage
        fields = [
            'name',
            'species',
            'order',
            'name_contains',
            'order_min',
            'order_max',
            'species_name',
        ]
