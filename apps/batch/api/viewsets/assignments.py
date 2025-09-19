"""
Batch container assignment viewsets.

These viewsets provide CRUD operations for batch container assignment management.
"""
from django.db.models import Sum, Count
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.authentication import TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.batch.models import BatchContainerAssignment
from apps.batch.api.serializers import BatchContainerAssignmentSerializer
from apps.batch.api.filters.assignments import BatchContainerAssignmentFilter
from .mixins import LocationFilterMixin


class BatchContainerAssignmentViewSet(LocationFilterMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Batch Container Assignments.

    This endpoint handles the assignment of batches (or parts of batches)
    to specific containers (e.g., tanks, ponds, cages) at a given point in time.
    It records the population count and biomass within that container.
    Provides full CRUD operations for these assignments.

    An assignment can be marked as inactive when a batch is moved out of a container.

    **Filtering:**
    - `batch`: ID of the assigned batch.
    - `batch__in`: Filter by multiple Batch IDs (comma-separated).
    - `container`: ID of the assigned container.
    - `container__in`: Filter by multiple Container IDs (comma-separated).
    - `is_active`: Boolean indicating if the assignment is currently active.
    - `assignment_date`: Exact date of the assignment.

    **Searching:**
    - `batch__batch_number`: Batch number of the assigned batch.
    - `container__name`: Name of the assigned container.

    **Ordering:**
    - `assignment_date` (default: descending)
    - `batch__batch_number`
    - `container__name`
    - `population_count`
    - `biomass_kg`
    """
    # authentication_classes = [TokenAuthentication, JWTAuthentication]
    # permission_classes = [IsAuthenticated]

    queryset = BatchContainerAssignment.objects.all()
    serializer_class = BatchContainerAssignmentSerializer
    filterset_class = BatchContainerAssignmentFilter
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['batch__batch_number', 'container__name']
    ordering_fields = [
        'assignment_date',
        'batch__batch_number',
        'container__name',
        'population_count',
        'biomass_kg'
    ]
    ordering = ['-assignment_date']

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
    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(30))
    @extend_schema(
        operation_id="batch-container-assignments-summary",
        summary="Get aggregated summary of batch container assignments",
        description="Returns aggregated metrics for batch container assignments with optional location-based filtering.",
        parameters=[
            OpenApiParameter(
                name="is_active",
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description="Filter by active status (default: true). Set to false to include inactive assignments.",
                required=False,
                default=True,
            ),
            OpenApiParameter(
                name="geography",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by geography ID. Affects containers in both halls and areas within this geography.",
                required=False,
            ),
            OpenApiParameter(
                name="area",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by area ID. Only affects containers directly assigned to this area.",
                required=False,
            ),
            OpenApiParameter(
                name="station",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by freshwater station ID. Only affects containers in halls within this station.",
                required=False,
            ),
            OpenApiParameter(
                name="hall",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by hall ID. Only affects containers directly in this hall.",
                required=False,
            ),
            OpenApiParameter(
                name="container_type",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by container type category. Valid values: TANK, PEN, TRAY, OTHER.",
                required=False,
            ),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "active_biomass_kg": {"type": "number", "description": "Total biomass in kg for active assignments"},
                    "count": {"type": "integer", "description": "Total number of assignments matching filters"},
                },
                "required": ["active_biomass_kg", "count"],
            },
            400: {
                "type": "object",
                "properties": {
                    "detail": {"type": "string"},
                    "geography": {"type": "array", "items": {"type": "string"}},
                    "area": {"type": "array", "items": {"type": "string"}},
                    "station": {"type": "array", "items": {"type": "string"}},
                    "hall": {"type": "array", "items": {"type": "string"}},
                    "container_type": {"type": "array", "items": {"type": "string"}},
                },
                "description": "Validation error for invalid filter parameters",
            },
        },
        examples=[
            {
                "summary": "Default summary (all active assignments)",
                "value": {
                    "active_biomass_kg": 1250.5,
                    "count": 45,
                },
            },
            {
                "summary": "Filtered by geography",
                "parameters": {"geography": 1},
                "value": {
                    "active_biomass_kg": 750.0,
                    "count": 28,
                },
            },
            {
                "summary": "Filtered by container type",
                "parameters": {"container_type": "TANK"},
                "value": {
                    "active_biomass_kg": 950.2,
                    "count": 32,
                },
            },
        ],
    )
    def summary(self, request):
        """
        Return aggregated metrics about batch-container assignments with optional location filtering.

        Query Parameters
        ----------------
        is_active : bool (default ``true``)
            If ``true`` (default) aggregates only active assignments.
            If ``false`` aggregates inactive assignments.
        geography : int
            Filter by geography ID (affects containers in halls and areas).
        area : int
            Filter by area ID (containers directly in this area).
        station : int
            Filter by freshwater station ID (containers in halls of this station).
        hall : int
            Filter by hall ID (containers directly in this hall).
        container_type : str
            Filter by container type category (TANK, PEN, TRAY, OTHER).

        Response Schema
        ---------------
        {
            "active_biomass_kg": number,
            "count": integer
        }
        """
        is_active_param = request.query_params.get("is_active", "true").lower()
        is_active = is_active_param != "false"

        assignments = self.get_queryset().filter(is_active=is_active)

        # Apply location filters
        assignments = self.apply_location_filters(assignments, request)

        aggregates = assignments.aggregate(
            active_biomass_kg=Sum("biomass_kg"),
            count=Count("id"),
        )

        return Response(
            {
                "active_biomass_kg": float(aggregates["active_biomass_kg"] or 0),
                "count": aggregates["count"] or 0,
            }
        )
