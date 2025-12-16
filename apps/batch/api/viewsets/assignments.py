"""
Batch container assignment viewsets.

These viewsets provide CRUD operations for batch container assignment
management, including live forward projection endpoints for growth forecasting.
"""
from datetime import date as date_cls
from django.db.models import Sum, Count
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from aquamind.api.mixins import RBACFilterMixin
from aquamind.api.permissions import IsOperator
from aquamind.utils.history_mixins import HistoryReasonMixin

from rest_framework.authentication import TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from apps.batch.models import BatchContainerAssignment, LiveForwardProjection
from apps.batch.api.serializers import BatchContainerAssignmentSerializer
from apps.batch.api.filters.assignments import BatchContainerAssignmentFilter
from .mixins import LocationFilterMixin


class BatchContainerAssignmentViewSet(RBACFilterMixin, HistoryReasonMixin, LocationFilterMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Batch Container Assignments.

    This endpoint handles the assignment of batches (or parts of batches)
    to specific containers (e.g., tanks, ponds, cages) at a given point in time.
    It records the population count and biomass within that container.
    Provides full CRUD operations for these assignments. Access is restricted to
    operational staff (Operators, Managers, and Admins).
    
    RBAC Enforcement:
    - Permission: IsOperator (OPERATOR/MANAGER/Admin)
    - Geographic Filtering: Users only see assignments in their geography
    - Object-level Validation: Prevents creating/updating assignments outside user's scope
    
    Uses HistoryReasonMixin to capture audit change reasons.

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
    permission_classes = [IsAuthenticated, IsOperator]
    
    # RBAC configuration - filter by geography through container
    # Support both area-based and hall-based containers
    geography_filter_fields = [
        'container__area__geography',  # Sea area containers
        'container__hall__freshwater_station__geography'  # Hall/station containers
    ]
    enable_operator_location_filtering = True  # Phase 2: Fine-grained operator filtering

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
                    "total_population": {"type": "integer", "description": "Total fish population count across all assignments"},
                },
                "required": ["active_biomass_kg", "count", "total_population"],
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
    )
    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(30))
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
            "count": integer,
            "total_population": integer
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
            total_population=Sum("population_count"),
        )

        return Response(
            {
                "active_biomass_kg": float(aggregates["active_biomass_kg"] or 0),
                "count": aggregates["count"] or 0,
                "total_population": aggregates["total_population"] or 0,
            }
        )

    # ------------------------------------------------------------------ #
    # Live Forward Projection endpoint                                   #
    # ------------------------------------------------------------------ #
    @extend_schema(
        operation_id="batch-container-assignments-live-forward-projection",
        summary="Get live forward projection for an assignment",
        description="""
Returns the live forward projection series for a specific container assignment.

The projection starts from the latest ActualDailyAssignmentState and projects
growth forward to the scenario end using:
- TGC-based growth model
- Temperature profile with bias adjustment
- Scenario mortality model

**Temperature Bias**: Computed from recent days where sensor-derived temps
were available (measured, interpolated, nearest). The bias represents the
delta between actual temps and profile temps, clamped to configurable bounds.

**Provenance**: Response includes full transparency about projection inputs:
- Temperature profile name and ID
- Bias value, window days, and clamp bounds
- TGC value used
- computed_date (when projection was run)

By default returns the latest projection (computed_date = most recent).
Use `computed_date` parameter for backtesting historical projections.
        """,
        parameters=[
            OpenApiParameter(
                name="computed_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Date of projection run (YYYY-MM-DD). Default: latest.",
                required=False,
            ),
        ],
        responses={
            200: OpenApiResponse(
                description="Live forward projection series with provenance",
                response={
                    "type": "object",
                    "properties": {
                        "assignment_id": {"type": "integer"},
                        "batch_number": {"type": "string"},
                        "container_name": {"type": "string"},
                        "computed_date": {
                            "type": "string",
                            "format": "date",
                            "description": "Date projection was computed"
                        },
                        "provenance": {
                            "type": "object",
                            "properties": {
                                "temp_profile_id": {"type": "integer"},
                                "temp_profile_name": {"type": "string"},
                                "temp_bias_c": {"type": "number"},
                                "temp_bias_window_days": {"type": "integer"},
                                "temp_bias_clamp_min_c": {"type": "number"},
                                "temp_bias_clamp_max_c": {"type": "number"},
                                "tgc_value": {"type": "number"},
                            }
                        },
                        "projections": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "projection_date": {
                                        "type": "string",
                                        "format": "date"
                                    },
                                    "day_number": {"type": "integer"},
                                    "projected_weight_g": {"type": "number"},
                                    "projected_population": {"type": "integer"},
                                    "projected_biomass_kg": {"type": "number"},
                                    "temperature_used_c": {"type": "number"},
                                }
                            }
                        }
                    }
                }
            ),
            404: OpenApiResponse(description="No projections found"),
        },
    )
    @action(detail=True, methods=['get'], url_path='live-forward-projection')
    def live_forward_projection(self, request, pk=None):
        """
        Get live forward projection series for this assignment.

        Returns projected growth trajectory from latest actual state,
        with full provenance about model inputs and temperature bias.
        """
        assignment = self.get_object()

        # Parse computed_date parameter (default: latest)
        computed_date_str = request.query_params.get('computed_date')
        if computed_date_str:
            try:
                computed_date = date_cls.fromisoformat(computed_date_str)
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            projections = LiveForwardProjection.objects.filter(
                assignment=assignment,
                computed_date=computed_date,
            ).order_by('projection_date')
        else:
            # Get latest computed_date for this assignment
            latest = LiveForwardProjection.objects.filter(
                assignment=assignment,
            ).order_by('-computed_date').first()

            if not latest:
                return Response(
                    {
                        "error": "No projections available",
                        "detail": "Live forward projections have not been "
                                  "computed for this assignment yet."
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

            computed_date = latest.computed_date
            projections = LiveForwardProjection.objects.filter(
                assignment=assignment,
                computed_date=computed_date,
            ).order_by('projection_date')

        if not projections.exists():
            return Response(
                {"error": "No projections found for specified date"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Build response with provenance from first projection
        first_proj = projections.first()

        response_data = {
            "assignment_id": assignment.id,
            "batch_number": assignment.batch.batch_number,
            "container_name": assignment.container.name,
            "computed_date": computed_date.isoformat(),
            "provenance": {
                "temp_profile_id": first_proj.temp_profile_id,
                "temp_profile_name": first_proj.temp_profile_name,
                "temp_bias_c": float(first_proj.temp_bias_c),
                "temp_bias_window_days": first_proj.temp_bias_window_days,
                "temp_bias_clamp_min_c": float(first_proj.temp_bias_clamp_min_c),
                "temp_bias_clamp_max_c": float(first_proj.temp_bias_clamp_max_c),
                "tgc_value": float(first_proj.tgc_value_used),
            },
            "projections": [
                {
                    "projection_date": proj.projection_date.isoformat(),
                    "day_number": proj.day_number,
                    "projected_weight_g": float(proj.projected_weight_g),
                    "projected_population": proj.projected_population,
                    "projected_biomass_kg": float(proj.projected_biomass_kg),
                    "temperature_used_c": float(proj.temperature_used_c),
                }
                for proj in projections
            ],
        }

        return Response(response_data)
