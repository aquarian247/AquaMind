"""
Area viewset for the infrastructure app.

This module defines the viewset for the Area model.
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import FilterSet
from django.db.models import Count, Sum, Q
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

from apps.infrastructure.models.area import Area
from apps.infrastructure.models.container import Container
from apps.batch.models.assignment import BatchContainerAssignment
from apps.infrastructure.api.serializers.area import AreaSerializer


class AreaFilter(FilterSet):
    """Custom filterset for Area model to support __in lookups."""

    class Meta:
        model = Area
        fields = {
            'name': ['exact', 'icontains'],
            'geography': ['exact', 'in'],
            'active': ['exact']
        }


class AreaViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Areas within the aquaculture facility.

    Areas represent distinct geographical or functional zones within a larger geography
    (e.g., a specific section of a farm). This endpoint allows for full CRUD operations
    on Area instances. Uses HistoryReasonMixin to capture audit change reasons.

    **Filtering:**
    - `name`: Filter by the exact name of the area.
    - `geography`: Filter by the ID of the parent Geography.
    - `geography__in`: Filter by multiple Geography IDs (comma-separated).
    - `active`: Filter by active status (boolean).

    **Searching:**
    - `name`: Search by area name (partial matches).
    - `geography__name`: Search by the name of the parent Geography (partial matches).

    **Ordering:**
    - `name` (default)
    - `geography__name`
    - `created_at`
    """
    # Explicitly override authentication to prevent SessionAuthentication fallback
    authentication_classes = [TokenAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = AreaFilter
    search_fields = ['name', 'geography__name']
    ordering_fields = ['name', 'geography__name', 'created_at']
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
        operation_id="area-summary",
        description="Get KPI summary for an area including container counts, biomass, population, and average weight.",
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
                        "container_count": {"type": "integer", "description": "Total number of containers in the area"},
                        "ring_count": {"type": "integer", "description": "Number of ring/pen containers in the area"},
                        "active_biomass_kg": {"type": "number", "description": "Total active biomass in kilograms"},
                        "population_count": {"type": "integer", "description": "Total population count"},
                        "avg_weight_kg": {"type": "number", "description": "Average weight in kilograms per fish"},
                    },
                    "required": ["container_count", "ring_count", "active_biomass_kg", "population_count", "avg_weight_kg"],
                },
                description="Area KPI metrics",
            )
        },
    )
    @method_decorator(cache_page(60))
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """
        Return KPI summary for a specific area.

        Computes aggregated metrics including:
        - container_count: Total containers in the area
        - ring_count: Containers that are rings/pens (category='PEN' or name contains 'Ring')
        - active_biomass_kg: Sum of biomass from active batch assignments
        - population_count: Sum of population from active batch assignments
        - avg_weight_kg: Biomass divided by population (0 if no population)

        Query Parameters:
        - is_active: Filter by active status (default: true)

        Returns:
            Response: JSON with aggregated area metrics
        """
        # Get the area object
        area = self.get_object()

        # Parse query parameters
        is_active_param = request.query_params.get("is_active", "true").lower()
        is_active_filter = is_active_param != "false"

        # Get containers in this area
        containers = Container.objects.filter(area=area)

        # Aggregate container counts
        container_aggregates = containers.aggregate(
            container_count=Count('id'),
            ring_count=Count('id', filter=Q(
                Q(container_type__category='PEN') |
                Q(container_type__name__icontains='ring') |
                Q(name__icontains='ring')
            )),
        )

        # Get biomass and population aggregates based on is_active filter
        if is_active_filter:
            # Default behavior: only active assignments
            biomass_aggregates = BatchContainerAssignment.objects.filter(
                container__area=area,
                is_active=True
            ).aggregate(
                active_biomass_kg=Sum('biomass_kg'),
                population_count=Sum('population_count'),
            )
        else:
            # Include all assignments (active and inactive)
            biomass_aggregates = BatchContainerAssignment.objects.filter(
                container__area=area
            ).aggregate(
                active_biomass_kg=Sum('biomass_kg'),
                population_count=Sum('population_count'),
            )

        # Extract values with defaults
        container_count = container_aggregates['container_count'] or 0
        ring_count = container_aggregates['ring_count'] or 0
        active_biomass_kg = float(biomass_aggregates['active_biomass_kg'] or 0)
        population_count = biomass_aggregates['population_count'] or 0

        # Calculate average weight with division by zero protection
        avg_weight_kg = active_biomass_kg / population_count if population_count > 0 else 0

        return Response({
            'container_count': container_count,
            'ring_count': ring_count,
            'active_biomass_kg': active_biomass_kg,
            'population_count': population_count,
            'avg_weight_kg': round(avg_weight_kg, 3),
        })
