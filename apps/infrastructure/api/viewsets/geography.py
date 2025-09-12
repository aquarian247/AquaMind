"""
Geography viewset for the infrastructure app.

This module defines the viewset for the Geography model.
"""

from django.db.models import Count, Sum, Q
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.infrastructure.models.geography import Geography
from apps.infrastructure.models.area import Area
from apps.infrastructure.models.station import FreshwaterStation
from apps.infrastructure.models.hall import Hall
from apps.infrastructure.models.container import Container
from apps.batch.models.assignment import BatchContainerAssignment
from apps.infrastructure.api.serializers.geography import GeographySerializer, GeographySummarySerializer
from rest_framework.authentication import TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated

class GeographyViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Geographical locations or zones.

    Geographies represent defined geographical areas relevant to the aquaculture
    operations, such as countries, regions, specific water bodies, or custom zones.
    These can be used to associate other entities (like facilities or environmental
    readings) with a spatial context.
    This endpoint allows for full CRUD operations on Geography instances.

    **Filtering:**
    - `name`: Filter by the exact name of the geography.

    **Searching:**
    - `name`: Search by geography name (partial matches).
    - `description`: Search within the description of the geography.

    **Ordering:**
    - `name` (default)
    - `created_at`
    """
    # Explicitly override authentication to prevent SessionAuthentication fallback
    authentication_classes = [TokenAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    queryset = Geography.objects.all()
    serializer_class = GeographySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
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

    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @method_decorator(cache_page(60), name="summary")
    @action(detail=True, methods=['get'], url_path="summary")
    @extend_schema(
        operation_id="geography-summary",
        description="Return KPI roll-up for a single Geography.",
        responses={
            200: GeographySummarySerializer,
        },
    )
    def summary(self, request, pk=None):
        """
        Return aggregated KPI metrics for a geography.

        Computes counts and sums for areas, stations, halls, containers,
        ring containers, capacity, and active biomass within the geography.
        """
        geography = self.get_object()

        # Count areas in geography
        area_count = Area.objects.filter(geography=geography).count()

        # Count stations in geography
        station_count = FreshwaterStation.objects.filter(geography=geography).count()

        # Count halls in geography (through stations)
        hall_count = Hall.objects.filter(
            freshwater_station__geography=geography
        ).count()

        # Count containers in geography (through areas or halls)
        container_count = Container.objects.filter(
            Q(area__geography=geography) | Q(hall__freshwater_station__geography=geography)
        ).count()

        # Count ring containers (container_type category contains "ring" or "pen")
        ring_count = Container.objects.filter(
            Q(area__geography=geography) | Q(hall__freshwater_station__geography=geography)
        ).filter(
            Q(container_type__category__icontains="ring") |
            Q(container_type__category__icontains="pen")
        ).count()

        # Sum capacity (max_biomass_kg from containers)
        capacity_result = Container.objects.filter(
            Q(area__geography=geography) | Q(hall__freshwater_station__geography=geography)
        ).aggregate(
            total_capacity=Sum('max_biomass_kg')
        )
        capacity_kg = float(capacity_result['total_capacity'] or 0)

        # Sum active biomass (active BatchContainerAssignment biomass_kg)
        active_biomass_result = BatchContainerAssignment.objects.filter(
            Q(container__area__geography=geography) | Q(container__hall__freshwater_station__geography=geography),
            is_active=True
        ).aggregate(
            total_biomass=Sum('biomass_kg')
        )
        active_biomass_kg = float(active_biomass_result['total_biomass'] or 0)

        # Return response data
        return Response({
            'area_count': area_count,
            'station_count': station_count,
            'hall_count': hall_count,
            'container_count': container_count,
            'ring_count': ring_count,
            'capacity_kg': capacity_kg,
            'active_biomass_kg': active_biomass_kg,
        })
