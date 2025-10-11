"""
Feeding event filters.

These filters provide advanced filtering for feeding event endpoints,
including geographic, nutritional, and cost-based filtering for finance reporting.
"""
import django_filters as filters
from django_filters import rest_framework as rest_filters
from apps.inventory.models import FeedingEvent


class FeedingEventFilter(rest_filters.FilterSet):
    """
    Advanced filter class for FeedingEvent model.

    Provides comprehensive filtering options for feeding event tracking and finance reporting,
    including multi-dimensional filtering by geography, feed properties, and costs.
    """

    # =========================================================================
    # Date Range Filters
    # =========================================================================
    feeding_date_after = filters.DateFilter(
        field_name='feeding_date',
        lookup_expr='gte',
        help_text="Filter feeding events on or after this date (YYYY-MM-DD)"
    )
    feeding_date_before = filters.DateFilter(
        field_name='feeding_date',
        lookup_expr='lte',
        help_text="Filter feeding events on or before this date (YYYY-MM-DD)"
    )

    # =========================================================================
    # Amount Range Filters
    # =========================================================================
    amount_min = filters.NumberFilter(
        field_name='amount_kg',
        lookup_expr='gte',
        help_text="Minimum feed amount in kg"
    )
    amount_max = filters.NumberFilter(
        field_name='amount_kg',
        lookup_expr='lte',
        help_text="Maximum feed amount in kg"
    )

    # =========================================================================
    # Geographic Dimension Filters (via Container relationships)
    # =========================================================================
    
    # Area filters
    area = filters.NumberFilter(
        field_name='container__area__id',
        help_text="Filter by area ID (via container → area)"
    )
    area__in = filters.BaseInFilter(
        field_name='container__area__id',
        help_text="Filter by multiple area IDs (comma-separated)"
    )
    
    # Geography filters
    geography = filters.NumberFilter(
        field_name='container__area__geography__id',
        help_text="Filter by geography ID (via container → area → geography)"
    )
    geography__in = filters.BaseInFilter(
        field_name='container__area__geography__id',
        help_text="Filter by multiple geography IDs (comma-separated)"
    )
    
    # Freshwater Station filters (via Hall)
    freshwater_station = filters.NumberFilter(
        field_name='container__hall__freshwater_station__id',
        help_text="Filter by freshwater station ID (via container → hall → station)"
    )
    freshwater_station__in = filters.BaseInFilter(
        field_name='container__hall__freshwater_station__id',
        help_text="Filter by multiple freshwater station IDs (comma-separated)"
    )
    
    # Hall filters
    hall = filters.NumberFilter(
        field_name='container__hall__id',
        help_text="Filter by hall ID (via container → hall)"
    )
    hall__in = filters.BaseInFilter(
        field_name='container__hall__id',
        help_text="Filter by multiple hall IDs (comma-separated)"
    )

    # =========================================================================
    # Feed Nutritional Property Filters
    # =========================================================================
    
    # Protein percentage filters
    feed__protein_percentage__gte = filters.NumberFilter(
        field_name='feed__protein_percentage',
        lookup_expr='gte',
        help_text="Minimum protein percentage (0-100)"
    )
    feed__protein_percentage__lte = filters.NumberFilter(
        field_name='feed__protein_percentage',
        lookup_expr='lte',
        help_text="Maximum protein percentage (0-100)"
    )
    
    # Fat percentage filters
    feed__fat_percentage__gte = filters.NumberFilter(
        field_name='feed__fat_percentage',
        lookup_expr='gte',
        help_text="Minimum fat percentage (0-100)"
    )
    feed__fat_percentage__lte = filters.NumberFilter(
        field_name='feed__fat_percentage',
        lookup_expr='lte',
        help_text="Maximum fat percentage (0-100)"
    )
    
    # Carbohydrate percentage filters
    feed__carbohydrate_percentage__gte = filters.NumberFilter(
        field_name='feed__carbohydrate_percentage',
        lookup_expr='gte',
        help_text="Minimum carbohydrate percentage (0-100)"
    )
    feed__carbohydrate_percentage__lte = filters.NumberFilter(
        field_name='feed__carbohydrate_percentage',
        lookup_expr='lte',
        help_text="Maximum carbohydrate percentage (0-100)"
    )
    
    # Brand filters
    feed__brand = filters.CharFilter(
        field_name='feed__brand',
        lookup_expr='iexact',
        help_text="Filter by exact feed brand (case-insensitive)"
    )
    feed__brand__in = filters.BaseInFilter(
        field_name='feed__brand',
        help_text="Filter by multiple brands (comma-separated)"
    )
    feed__brand__icontains = filters.CharFilter(
        field_name='feed__brand',
        lookup_expr='icontains',
        help_text="Filter by partial brand name (case-insensitive)"
    )
    
    # Size category filters
    feed__size_category = filters.ChoiceFilter(
        field_name='feed__size_category',
        choices=[
            ('MICRO', 'Micro'),
            ('SMALL', 'Small'),
            ('MEDIUM', 'Medium'),
            ('LARGE', 'Large'),
        ],
        help_text="Filter by feed size category"
    )
    feed__size_category__in = filters.MultipleChoiceFilter(
        field_name='feed__size_category',
        choices=[
            ('MICRO', 'Micro'),
            ('SMALL', 'Small'),
            ('MEDIUM', 'Medium'),
            ('LARGE', 'Large'),
        ],
        help_text="Filter by multiple size categories"
    )

    # =========================================================================
    # Cost-Based Filters
    # =========================================================================
    
    # Feed cost filters (cost of the feeding event itself)
    feed_cost__gte = filters.NumberFilter(
        field_name='feed_cost',
        lookup_expr='gte',
        help_text="Minimum feed cost for the event"
    )
    feed_cost__lte = filters.NumberFilter(
        field_name='feed_cost',
        lookup_expr='lte',
        help_text="Maximum feed cost for the event"
    )

    # =========================================================================
    # Legacy Filters (maintained for backward compatibility)
    # =========================================================================
    
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
