"""
Mortality viewsets for health monitoring.

This module defines viewsets for mortality-related models, including
MortalityReason, MortalityRecord, and LiceCount.
"""

from rest_framework import viewsets, permissions
from django_filters import rest_framework as filters
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.db.models import Sum, Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from datetime import timedelta
from django.utils import timezone

from apps.health.models import (
    MortalityReason, MortalityRecord, LiceCount, LiceType
)
from apps.health.api.serializers import (
    MortalityReasonSerializer,
    MortalityRecordSerializer,
    LiceCountSerializer,
    LiceTypeSerializer
)
from apps.health.api.permissions import IsHealthContributor
from aquamind.api.mixins import RBACFilterMixin
from aquamind.utils.history_mixins import HistoryReasonMixin
from ..mixins import (
    UserAssignmentMixin, OptimizedQuerysetMixin, StandardFilterMixin
)


class MortalityReasonFilter(filters.FilterSet):
    top_level = filters.BooleanFilter(method='filter_top_level')
    parent = filters.NumberFilter(field_name='parent_id')

    def filter_top_level(self, queryset, name, value):
        if value:
            return queryset.filter(parent__isnull=True)
        return queryset

    class Meta:
        model = MortalityReason
        fields = {
            'name': ['exact', 'icontains']
        }


class MortalityReasonViewSet(
    HistoryReasonMixin, StandardFilterMixin,
    viewsets.ModelViewSet
):
    """
    API endpoint for managing Mortality Reasons.

    Provides CRUD operations for mortality reasons used in
    mortality records. Access restricted to health contributors.
    
    RBAC Enforcement:
    - Permission: IsHealthContributor (VET/QA/Admin)
    - No geographic filtering (mortality reasons are global reference data)

    Uses HistoryReasonMixin to automatically capture change
    reasons for audit trails.
    """
    queryset = MortalityReason.objects.all()
    serializer_class = MortalityReasonSerializer
    permission_classes = [permissions.IsAuthenticated, IsHealthContributor]
    filterset_class = MortalityReasonFilter

    # Override filter_queryset to add custom filtering
    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)

        # Manual filtering for category
        category = self.request.query_params.get('category')

        if category is not None:
            queryset = queryset.filter(category=category)

        return queryset
    search_fields = ['name', 'description']

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='top_level',
                type=bool,
                description='Filter to only top-level reasons (no parent)',
                required=False,
            ),
            OpenApiParameter(
                name='parent',
                type=int,
                description='Filter by parent reason ID',
                required=False,
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class MortalityRecordViewSet(
    RBACFilterMixin, HistoryReasonMixin, OptimizedQuerysetMixin,
    StandardFilterMixin, viewsets.ModelViewSet
):
    """
    API endpoint for managing Mortality Records.

    Provides CRUD operations for mortality records, which track
    fish deaths and their causes. Access restricted to health contributors.
    
    RBAC Enforcement:
    - Permission: IsHealthContributor (VET/QA/Admin)
    - Geographic Filtering: Users only see records for batches in their geography
    - Object-level Validation: Prevents creating/updating records outside user's scope

    Note: UserAssignmentMixin removed as MortalityRecord has
    no user field. Uses HistoryReasonMixin to automatically
    capture change reasons for audit trails.
    """
    queryset = MortalityRecord.objects.all()
    serializer_class = MortalityRecordSerializer
    permission_classes = [permissions.IsAuthenticated, IsHealthContributor]
    
    # RBAC configuration - filter by geography through batch
    geography_filter_fields = [
        'batch__batch_assignments__container__area__geography',
        'batch__batch_assignments__container__hall__freshwater_station__geography'
    ]

    # OptimizedQuerysetMixin configuration
    select_related_fields = ['batch', 'container', 'reason']

    # StandardFilterMixin configuration
    filterset_fields = {
        'event_date': ['exact', 'gte', 'lte'],
        'batch': ['exact'],
        'container': ['exact'],
        'reason': ['exact'],
        'count': ['exact', 'gte', 'lte']
    }

    search_fields = ['notes']


class LiceCountViewSet(
    RBACFilterMixin, HistoryReasonMixin, UserAssignmentMixin,
    OptimizedQuerysetMixin, StandardFilterMixin,
    viewsets.ModelViewSet
):
    """
    API endpoint for managing Lice Counts.
    
    Access restricted to health contributors (VET/QA/Admin).
    
    RBAC Enforcement:
    - Permission: IsHealthContributor (VET/QA/Admin)
    - Geographic Filtering: Users only see lice counts for batches in their geography
    - Object-level Validation: Prevents creating/updating counts outside user's scope

    Provides CRUD operations for lice counts, which track sea
    lice infestations in fish populations.

    Note: UserAssignmentMixin is appropriate here as LiceCount
    has a user field. Uses HistoryReasonMixin to automatically
    capture change reasons for audit trails.
    """
    queryset = LiceCount.objects.all()
    serializer_class = LiceCountSerializer
    permission_classes = [permissions.IsAuthenticated, IsHealthContributor]
    
    # RBAC configuration - filter by geography through batch
    geography_filter_fields = [
        'batch__batch_assignments__container__area__geography',
        'batch__batch_assignments__container__hall__freshwater_station__geography'
    ]

    # OptimizedQuerysetMixin configuration
    select_related_fields = ['user', 'batch', 'container']

    # StandardFilterMixin configuration - using only actual model fields
    filterset_fields = {
        'count_date': ['exact', 'gte', 'lte'],
        'batch': ['exact'],
        'container': ['exact'],
        'user': ['exact'],
        'lice_type': ['exact'],
        'fish_sampled': ['exact', 'gte', 'lte'],
        'adult_female_count': ['exact', 'gte', 'lte'],
        'adult_male_count': ['exact', 'gte', 'lte'],
        'juvenile_count': ['exact', 'gte', 'lte'],
        'count_value': ['exact', 'gte', 'lte'],
    }

    search_fields = ['notes']

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='geography',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by geography ID'
            ),
            OpenApiParameter(
                name='area',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by area ID'
            ),
            OpenApiParameter(
                name='start_date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description=(
                    'Start date for filtering (YYYY-MM-DD)'
                )
            ),
            OpenApiParameter(
                name='end_date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description=(
                    'End date for filtering (YYYY-MM-DD)'
                )
            ),
        ],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'total_counts': {
                        'type': 'integer',
                        'description': 'Total lice counted'
                    },
                    'average_per_fish': {
                        'type': 'number',
                        'description': 'Average lice per fish'
                    },
                    'fish_sampled': {
                        'type': 'integer',
                        'description': 'Total fish sampled'
                    },
                    'by_species': {
                        'type': 'object',
                        'description': 'Counts grouped by species',
                        'additionalProperties': {'type': 'integer'}
                    },
                    'by_development_stage': {
                        'type': 'object',
                        'description': 'Counts by development stage',
                        'additionalProperties': {'type': 'integer'}
                    },
                    'alert_level': {
                        'type': 'string',
                        'enum': ['good', 'warning', 'critical'],
                        'description': 'Alert level by thresholds'
                    },
                }
            }
        },
        description=(
            'Get aggregated lice summary with optional geography, '
            'area, and date filtering.'
        )
    )
    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(60))
    def summary(self, request):  # noqa: C901
        """
        Get aggregated lice count summary.

        Returns summary statistics including total counts, averages,
        and breakdowns by species and development stage. Supports
        filtering by geography, area, and date range.
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Apply additional filters from query params
        geography_id = request.query_params.get('geography')
        area_id = request.query_params.get('area')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if geography_id:
            # Filter by geography through container relationships
            queryset = queryset.filter(
                Q(container__area__geography_id=geography_id) |
                Q(container__hall__freshwater_station__geography_id=geography_id)  # noqa: E501
            )

        if area_id:
            queryset = queryset.filter(container__area_id=area_id)

        if start_date:
            queryset = queryset.filter(count_date__gte=start_date)

        if end_date:
            queryset = queryset.filter(count_date__lte=end_date)

        # Calculate aggregations
        total_counts = 0
        fish_sampled = 0
        by_species = {}
        by_development_stage = {}

        for count in queryset.select_related('lice_type'):
            fish_sampled += count.fish_sampled
            count_total = count.total_count
            total_counts += count_total

            # Aggregate by species/stage if using new format
            if count.lice_type:
                species = count.lice_type.species
                stage = count.lice_type.development_stage

                by_species[species] = (
                    by_species.get(species, 0) + count.count_value
                )
                by_development_stage[stage] = (
                    by_development_stage.get(stage, 0) +
                    count.count_value
                )

        # Calculate average per fish
        average_per_fish = (
            total_counts / fish_sampled if fish_sampled > 0 else 0
        )

        # Determine alert level based on thresholds
        # Mature lice: < 0.5 good, 0.5-1.0 warning, > 1.0 critical
        alert_level = 'good'
        if average_per_fish >= 1.0:
            alert_level = 'critical'
        elif average_per_fish >= 0.5:
            alert_level = 'warning'

        return Response({
            'total_counts': total_counts,
            'average_per_fish': round(average_per_fish, 2),
            'fish_sampled': fish_sampled,
            'by_species': by_species,
            'by_development_stage': by_development_stage,
            'alert_level': alert_level,
        })

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='geography',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by geography ID'
            ),
            OpenApiParameter(
                name='area',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by area ID'
            ),
            OpenApiParameter(
                name='start_date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description=(
                    'Start date for trends (YYYY-MM-DD). '
                    'Defaults to 1 year ago.'
                )
            ),
            OpenApiParameter(
                name='end_date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description=(
                    'End date for trends (YYYY-MM-DD). '
                    'Defaults to today.'
                )
            ),
            OpenApiParameter(
                name='interval',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Interval: weekly or monthly',
                enum=['weekly', 'monthly'],
            ),
        ],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'trends': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'period': {
                                    'type': 'string',
                                    'description': (
                                        'Week or month identifier'
                                    )
                                },
                                'average_per_fish': {
                                    'type': 'number'
                                },
                                'total_counts': {
                                    'type': 'integer'
                                },
                                'fish_sampled': {
                                    'type': 'integer'
                                },
                            }
                        }
                    }
                }
            }
        },
        description=(
            'Get lice count trends over time with '
            'weekly or monthly aggregation.'
        )
    )
    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(60))
    def trends(self, request):  # noqa: C901
        """
        Get lice count trends over time.

        Returns time-series data showing lice count trends with
        configurable aggregation intervals (weekly or monthly).
        Useful for multi-year historical analysis.
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Apply filters
        geography_id = request.query_params.get('geography')
        area_id = request.query_params.get('area')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        interval = request.query_params.get('interval', 'weekly')

        # Default date range: last year
        if not end_date:
            end_date = timezone.now().date()
        else:
            from datetime import datetime
            end_date = datetime.strptime(
                end_date, '%Y-%m-%d'
            ).date()

        if not start_date:
            start_date = end_date - timedelta(days=365)
        else:
            from datetime import datetime
            start_date = datetime.strptime(
                start_date, '%Y-%m-%d'
            ).date()

        queryset = queryset.filter(
            count_date__gte=start_date,
            count_date__lte=end_date
        )

        if geography_id:
            queryset = queryset.filter(
                Q(container__area__geography_id=geography_id) |
                Q(container__hall__freshwater_station__geography_id=geography_id)  # noqa: E501
            )

        if area_id:
            queryset = queryset.filter(container__area_id=area_id)

        # Group by time period
        from django.db.models.functions import TruncWeek, TruncMonth

        if interval == 'monthly':
            queryset = queryset.annotate(
                period=TruncMonth('count_date')
            )
        else:
            queryset = queryset.annotate(
                period=TruncWeek('count_date')
            )

        # Aggregate by period
        trends_data = []
        grouped = queryset.values('period').annotate(
            total_fish=Sum('fish_sampled'),
            total_counts=Sum('count_value'),
            legacy_total=(
                Sum('adult_female_count') +
                Sum('adult_male_count') +
                Sum('juvenile_count')
            )
        ).order_by('period')

        for group in grouped:
            # Use new format if available, otherwise legacy
            total = (
                group['total_counts']
                if group['total_counts'] is not None
                else group['legacy_total']
            )
            avg = (
                total / group['total_fish']
                if group['total_fish'] > 0
                else 0
            )

            trends_data.append({
                'period': (
                    group['period'].isoformat()
                    if group['period']
                    else None
                ),
                'average_per_fish': round(avg, 2),
                'total_counts': total or 0,
                'fish_sampled': group['total_fish'] or 0,
            })

        return Response({'trends': trends_data})


class LiceTypeViewSet(
    HistoryReasonMixin, StandardFilterMixin,
    viewsets.ReadOnlyModelViewSet
):
    """
    API endpoint for Lice Type classifications (Read-Only).

    Provides access to normalized lice type lookup table with
    species, gender, and development stage classifications. This
    is a read-only endpoint; new lice types are managed by
    administrators through Django admin.
    """
    queryset = LiceType.objects.filter(is_active=True)
    serializer_class = LiceTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

    # StandardFilterMixin configuration
    filterset_fields = {
        'species': ['exact', 'icontains'],
        'gender': ['exact'],
        'development_stage': ['exact', 'icontains'],
        'is_active': ['exact']
    }

    search_fields = ['species', 'development_stage', 'description']
