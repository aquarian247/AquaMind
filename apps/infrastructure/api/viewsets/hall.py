"""
Hall viewset for the infrastructure app.

This module defines the viewset for the Hall model.
"""

from decimal import Decimal
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import FilterSet
from django.db.models import Count, Sum
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from rest_framework.authentication import TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from aquamind.utils.history_mixins import HistoryReasonMixin

from apps.infrastructure.models.hall import Hall
from apps.infrastructure.models.container import Container
from apps.batch.models.assignment import BatchContainerAssignment
from apps.infrastructure.api.serializers.hall import HallSerializer, HallSummarySerializer


class HallFilter(FilterSet):
    """Custom filterset for Hall model to support __in lookups."""

    class Meta:
        model = Hall
        fields = {
            'name': ['exact'],
            'freshwater_station': ['exact', 'in'],
            'active': ['exact']
        }


class HallViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Halls within the aquaculture facility.

    Halls represent distinct buildings or sections within the facility,
    often containing multiple containers or systems. They can be associated
    with a Freshwater Station.
    This endpoint allows for full CRUD operations on Hall instances. Uses
    HistoryReasonMixin to capture audit change reasons.

    **Filtering:**
    - `name`: Filter by the exact name of the hall.
    - `freshwater_station`: Filter by the ID of the associated Freshwater Station.
    - `freshwater_station__in`: Filter by multiple Freshwater Station IDs (comma-separated).
    - `active`: Filter by active status (boolean).

    **Searching:**
    - `name`: Search by hall name (partial matches).
    - `description`: Search within the description of the hall.
    - `freshwater_station__name`: Search by the name of the associated Freshwater Station.

    **Ordering:**
    - `name` (default)
    - `freshwater_station__name`: Order by the name of the associated Freshwater Station.
    - `created_at`
    """
    # Explicitly override authentication to prevent SessionAuthentication fallback
    authentication_classes = [TokenAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    queryset = Hall.objects.all()
    serializer_class = HallSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = HallFilter
    search_fields = ['name', 'description', 'freshwater_station__name']
    ordering_fields = ['name', 'freshwater_station__name', 'created_at']
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

    # ------------------------------------------------------------------ #
    # Aggregated summary endpoint                                        #
    # ------------------------------------------------------------------ #
    @extend_schema(
        operation_id="hall-summary",
        description="Get KPI summary for a hall including container counts, biomass, population, and average weight.",
        parameters=[
            OpenApiParameter(
                name="is_active",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Filter assignments by active status (default: true).",
                required=False,
                default=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {
                        "container_count": {"type": "integer", "description": "Total number of containers in the hall"},
                        "active_biomass_kg": {"type": "number", "description": "Total active biomass in kilograms"},
                        "population_count": {"type": "integer", "description": "Total population count"},
                        "avg_weight_kg": {"type": "number", "description": "Average weight in kilograms per fish"},
                    },
                    "required": ["container_count", "active_biomass_kg", "population_count", "avg_weight_kg"],
                },
                description="Hall KPI metrics",
            )
        },
        tags=["Infrastructure"],
    )
    @method_decorator(cache_page(60))
    @action(detail=True, methods=['get'], url_path='summary')
    def summary(self, request, pk=None):
        """
        Return KPI summary for a specific hall.

        Computes aggregated metrics including:
        - container_count: Total containers in the hall
        - active_biomass_kg: Sum of biomass from active batch assignments
        - population_count: Sum of population from active batch assignments
        - avg_weight_kg: Biomass divided by population (0 if no population)

        Query Parameters:
        - is_active: Filter by active status (default: true)

        Returns:
            Response: JSON with aggregated hall metrics
        """
        # Get the hall object
        hall = self.get_object()

        # Parse query parameters
        is_active_param = request.query_params.get("is_active", "true").lower()
        is_active_filter = is_active_param != "false"

        # Get containers in this hall
        containers = Container.objects.filter(hall=hall)

        # Aggregate container counts and total capacity
        container_aggregates = containers.aggregate(
            container_count=Count('id'),
            total_capacity_kg=Sum('max_biomass_kg'),
        )

        # Get biomass and population aggregates based on is_active filter
        if is_active_filter:
            # Default behavior: only active assignments
            biomass_aggregates = BatchContainerAssignment.objects.filter(
                container__hall=hall,
                is_active=True
            ).aggregate(
                active_biomass_kg=Sum('biomass_kg'),
                population_count=Sum('population_count'),
            )
        else:
            # Include all assignments (active and inactive)
            biomass_aggregates = BatchContainerAssignment.objects.filter(
                container__hall=hall
            ).aggregate(
                active_biomass_kg=Sum('biomass_kg'),
                population_count=Sum('population_count'),
            )

        # Extract values with defaults
        container_count = container_aggregates['container_count'] or 0
        total_capacity_kg = container_aggregates['total_capacity_kg'] or Decimal('0.00')
        active_biomass_kg = biomass_aggregates['active_biomass_kg'] or Decimal('0.00')
        population_count = biomass_aggregates['population_count'] or 0

        # Calculate average weight with division by zero protection
        avg_weight_kg = float(active_biomass_kg) / population_count if population_count > 0 else 0
        
        # Calculate utilization percentage (biomass-based)
        utilization_percent = float(active_biomass_kg) / float(total_capacity_kg) * 100 if total_capacity_kg > 0 else 0

        # Serialize and return the response
        serializer = HallSummarySerializer(data={
            'container_count': container_count,
            'active_biomass_kg': active_biomass_kg,
            'population_count': population_count,
            'avg_weight_kg': round(avg_weight_kg, 3),
            'total_capacity_kg': total_capacity_kg,
            'utilization_percent': round(utilization_percent, 1),
        })
        serializer.is_valid(raise_exception=True)

        return Response(serializer.validated_data)
