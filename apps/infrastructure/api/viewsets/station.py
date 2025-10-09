"""
FreshwaterStation viewset for the infrastructure app.

This module defines the viewset for the FreshwaterStation model.
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import FilterSet
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.db.models import Count, Sum
from drf_spectacular.utils import extend_schema

from aquamind.utils.history_mixins import HistoryReasonMixin

from apps.infrastructure.models.station import FreshwaterStation
from apps.infrastructure.models.hall import Hall
from apps.infrastructure.models.container import Container
from apps.batch.models.assignment import BatchContainerAssignment
from apps.infrastructure.api.serializers.station import FreshwaterStationSerializer, FreshwaterStationSummarySerializer


class FreshwaterStationFilter(FilterSet):
    """Custom filterset for FreshwaterStation model to support __in lookups."""

    class Meta:
        model = FreshwaterStation
        fields = {
            'name': ['exact', 'icontains'],
            'station_type': ['exact'],
            'geography': ['exact', 'in'],
            'active': ['exact']
        }


class FreshwaterStationViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Freshwater Stations.

    Freshwater Stations represent sources of freshwater for the aquaculture facility,
    such as wells, boreholes, or municipal supplies. They can be categorized by type
    and associated with a specific geographical location.
    This endpoint allows for full CRUD operations on FreshwaterStation instances.
    Uses HistoryReasonMixin to capture audit change reasons.

    **Filtering:**
    - `name`: Filter by the exact name of the freshwater station.
    - `station_type`: Filter by the type of station (e.g., WELL, BOREHOLE, MUNICIPAL).
    - `geography`: Filter by the ID of the associated Geography.
    - `geography__in`: Filter by multiple Geography IDs (comma-separated).
    - `active`: Filter by active status (boolean).

    **Searching:**
    - `name`: Search by station name (partial matches).
    - `description`: Search within the description of the station.
    - `geography__name`: Search by the name of the associated Geography.

    **Ordering:**
    - `name` (default)
    - `station_type`
    - `geography__name`: Order by the name of the associated Geography.
    - `created_at`
    """
    
    queryset = FreshwaterStation.objects.all()
    serializer_class = FreshwaterStationSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = FreshwaterStationFilter
    search_fields = ['name', 'description', 'geography__name']
    ordering_fields = ['name', 'station_type', 'geography__name', 'created_at']
    ordering = ['name']

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @method_decorator(cache_page(60))
    @action(detail=True, methods=['get'], url_path='summary')
    @extend_schema(
        operation_id="freshwater-station-summary",
        description="Return KPI roll-up for a single Freshwater Station including hall/container counts and active biomass metrics.",
        responses={
            200: FreshwaterStationSummarySerializer,
        },
        tags=["Infrastructure"],
    )
    def summary(self, request, pk=None):
        """
        Return aggregated KPI metrics for a freshwater station.

        Calculates:
        - hall_count: Number of halls in this station
        - container_count: Number of containers in those halls
        - active_biomass_kg: Sum of biomass from active assignments in those containers
        - population_count: Sum of population from active assignments in those containers
        - avg_weight_kg: biomass/population (0 if population=0)

        Uses database-level aggregation for optimal performance.
        """
        station = self.get_object()

        # Get hall count for this station
        hall_count = Hall.objects.filter(freshwater_station=station).count()

        # Get container count in halls of this station
        container_count = Container.objects.filter(hall__freshwater_station=station).count()

        # Aggregate active biomass and population from assignments in those containers
        assignment_aggregates = BatchContainerAssignment.objects.filter(
            container__hall__freshwater_station=station,
            is_active=True
        ).aggregate(
            active_biomass_kg=Sum('biomass_kg'),
            population_count=Sum('population_count')
        )

        # Extract values, defaulting to 0 for None results
        active_biomass_kg = float(assignment_aggregates['active_biomass_kg'] or 0)
        population_count = assignment_aggregates['population_count'] or 0

        # Calculate average weight with division-by-zero protection
        avg_weight_kg = active_biomass_kg / population_count if population_count > 0 else 0

        # Serialize and return the response
        serializer = FreshwaterStationSummarySerializer(data={
            'hall_count': hall_count,
            'container_count': container_count,
            'active_biomass_kg': active_biomass_kg,
            'population_count': population_count,
            'avg_weight_kg': round(avg_weight_kg, 3)
        })
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data)

    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
