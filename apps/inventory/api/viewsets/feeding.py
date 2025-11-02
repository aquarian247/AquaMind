"""
Feeding event viewset for the inventory app.
"""
import logging
from rest_framework import viewsets, filters, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.db.models import Count, Sum
from datetime import date, datetime
from django.utils import timezone

from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.inventory.models import FeedingEvent
from apps.inventory.api.serializers.feeding import FeedingEventSerializer
from apps.inventory.api.filters.feeding import FeedingEventFilter
from apps.inventory.services import FinanceReportingService
from aquamind.api.mixins import RBACFilterMixin
from aquamind.api.permissions import IsOperator
from aquamind.utils.history_mixins import HistoryReasonMixin

logger = logging.getLogger(__name__)


class FeedingEventViewSet(RBACFilterMixin, HistoryReasonMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Feeding Events in aquaculture operations.

    Feeding events record the amount of feed given to batches in specific containers
    on particular dates. This endpoint provides full CRUD operations for feeding events.
    Access is restricted to operational staff (Operators, Managers, and Admins).
    
    RBAC Enforcement:
    - Permission: IsOperator (OPERATOR/MANAGER/Admin)
    - Geographic Filtering: Users only see feeding events in their geography
    - Object-level Validation: Prevents creating/updating events outside user's scope
    
    Uses HistoryReasonMixin to capture audit change reasons.

    **Filtering:**
    - `batch`: ID of the batch being fed.
    - `batch__in`: Filter by multiple Batch IDs (comma-separated).
    - `feed`: ID of the feed type used.
    - `feed__in`: Filter by multiple Feed IDs (comma-separated).
    - `container`: ID of the container where feeding occurred.
    - `container__in`: Filter by multiple Container IDs (comma-separated).
    - `feeding_date`: Exact date of feeding.
    - `method`: Feeding method (e.g., 'MANUAL', 'AUTOMATIC').

    **Searching:**
    - `notes`: Notes associated with the feeding event.

    **Ordering:**
    - `feeding_date` (default: descending)
    - `feeding_time`
    - `amount_kg`
    """
    queryset = FeedingEvent.objects.all()
    serializer_class = FeedingEventSerializer
    permission_classes = [permissions.IsAuthenticated, IsOperator]
    
    # RBAC configuration - filter by geography through container -> area
    geography_filter_field = 'container__area__geography'
    enable_operator_location_filtering = True  # Phase 2: Fine-grained operator filtering
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_class = FeedingEventFilter
    search_fields = ['notes']
    ordering_fields = ['feeding_date', 'feeding_time', 'amount_kg']
    ordering = ['-feeding_date', '-feeding_time']

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='batch_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='ID of the batch to fetch feeding events for.',
                required=True,
            ),
        ],
        responses=FeedingEventSerializer(many=True),
    )
    @action(detail=False, methods=['get'])
    def by_batch(self, request):
        """
        Get feeding events for a specific batch.
        """
        batch_id = request.query_params.get('batch_id')
        if not batch_id:
            return Response(
                {"error": "batch_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        feeding_events = self.get_queryset().filter(batch_id=batch_id)
        serializer = self.get_serializer(feeding_events, many=True)
        return Response(serializer.data)

    # ------------------------------------------------------------------ #
    # Aggregated summary endpoint                                        #
    # ------------------------------------------------------------------ #
    @extend_schema(
        operation_id="feeding-events-summary",
        summary="Get aggregated feeding events summary with date filtering",
        description="Returns aggregated statistics for feeding events with support for both single date and date range filtering.",
        parameters=[
            OpenApiParameter(
                name="date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Single date to filter feeding events (YYYY-MM-DD) or 'today' (default).",
                required=False,
            ),
            OpenApiParameter(
                name="start_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Start date for range filtering (YYYY-MM-DD). Must be provided with end_date.",
                required=False,
            ),
            OpenApiParameter(
                name="end_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="End date for range filtering (YYYY-MM-DD). Must be provided with start_date.",
                required=False,
            ),
            OpenApiParameter(
                name="batch",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by batch ID.",
                required=False,
            ),
            OpenApiParameter(
                name="container",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter by container ID.",
                required=False,
            ),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "events_count": {"type": "integer", "description": "Number of feeding events"},
                    "total_feed_kg": {"type": "number", "description": "Total feed amount in kg"},
                    "total_feed_cost": {"type": "number", "description": "Total feed cost"},
                },
                "required": ["events_count", "total_feed_kg", "total_feed_cost"],
            },
            400: {
                "type": "object",
                "properties": {
                    "error": {"type": "string", "description": "Error message for invalid parameters"},
                },
                "description": "Bad request due to invalid date parameters",
            },
        },
    )
    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(30))  # Cache for 30 seconds
    def summary(self, request):
        """
        Return aggregated statistics for feeding events.

        Optional query parameters
        ------------------------
        date         : 'today' (default) or specific ISO date (YYYY-MM-DD)
        start_date   : Start date for range filtering (YYYY-MM-DD)
        end_date     : End date for range filtering (YYYY-MM-DD)
        batch        : Batch ID to filter by
        container    : Container ID to filter by

        Date Filtering Rules
        -------------------
        - Range parameters (start_date/end_date) take precedence over date parameter
        - Both start_date and end_date must be provided together
        - start_date must be before or equal to end_date
        - If no date parameters provided, defaults to today's date
        - Use date parameter for backward compatibility

        Response schema
        ----------------
        {
            "events_count": integer,
            "total_feed_kg": number,
            "total_feed_cost": number
        }
        """
        # Base queryset
        qs = self.get_queryset()

        # --- Filter by date or date range ------------------------------------
        # Check for date range parameters
        start_date_param = request.query_params.get("start_date")
        end_date_param = request.query_params.get("end_date")
        date_param = request.query_params.get("date", "today")

        # Validation: if only one of start_date/end_date is provided, return 400
        if (start_date_param and not end_date_param) or (not start_date_param and end_date_param):
            return Response(
                {"error": "Both start_date and end_date must be provided together"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if start_date_param and end_date_param:
            # Range mode: precedence over single date
            try:
                start_date = datetime.fromisoformat(start_date_param).date()
                end_date = datetime.fromisoformat(end_date_param).date()

                if start_date > end_date:
                    return Response(
                        {"error": "start_date must be before or equal to end_date"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                qs = qs.filter(feeding_date__range=(start_date, end_date))
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # Single date mode or default (maintains backward compatibility)
            if date_param == "today" or date_param == "":
                target_date = timezone.now().date()
                qs = qs.filter(feeding_date=target_date)
            else:
                try:
                    parsed_date = datetime.fromisoformat(date_param).date()
                    qs = qs.filter(feeding_date=parsed_date)
                except ValueError:
                    # Invalid date string -> ignore date filter
                    pass

        # --- Filter by batch -------------------------------------------------
        batch_param = request.query_params.get("batch")
        if batch_param:
            qs = qs.filter(batch_id=batch_param)

        # --- Filter by container --------------------------------------------
        container_param = request.query_params.get("container")
        if container_param:
            qs = qs.filter(container_id=container_param)

        aggregates = qs.aggregate(
            events_count=Count("id"),
            total_feed_kg=Sum("amount_kg"),
            total_feed_cost=Sum("feed_cost"),
        )

        return Response(
            {
                "events_count": aggregates["events_count"] or 0,
                "total_feed_kg": float(aggregates["total_feed_kg"] or 0),
                "total_feed_cost": float(aggregates["total_feed_cost"] or 0),
            }
        )
    
    # ------------------------------------------------------------------ #
    # Finance Report Endpoint (Comprehensive Multi-Dimensional Analysis) #
    # ------------------------------------------------------------------ #
    @extend_schema(
        operation_id="feeding-events-finance-report",
        summary="Comprehensive finance report with flexible filtering and aggregations",
        description="""
        Provides detailed feed usage and cost analysis with multi-dimensional filtering.
        
        Supports filtering by:
        - Time periods (date ranges via feeding_date_after/before)
        - Geography (geography, area, freshwater_station, hall, container)
        - Feed properties (protein %, fat %, carb %, brand, size category)
        - Cost ranges (feed_cost)
        - Feed types (feed, feed__in)
        
        Returns aggregated totals and optional breakdowns by selected dimensions.
        All filters from FeedingEventFilter are supported.
        """,
        parameters=[
            # Date filters (required for finance reports)
            OpenApiParameter(
                name='start_date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Start date for report period (YYYY-MM-DD) - REQUIRED',
                required=True,
            ),
            OpenApiParameter(
                name='end_date',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='End date for report period (YYYY-MM-DD) - REQUIRED',
                required=True,
            ),
            # Geographic filters
            OpenApiParameter(
                name='geography',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by geography ID (e.g., 1=Scotland, 2=Faroe Islands)',
                required=False,
            ),
            OpenApiParameter(
                name='geography__in',
                type={'type': 'array', 'items': {'type': 'integer'}},
                location=OpenApiParameter.QUERY,
                description='Filter by multiple geography IDs (comma-separated)',
                required=False,
            ),
            OpenApiParameter(
                name='area',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by area ID',
                required=False,
            ),
            OpenApiParameter(
                name='area__in',
                type={'type': 'array', 'items': {'type': 'integer'}},
                location=OpenApiParameter.QUERY,
                description='Filter by multiple area IDs (comma-separated)',
                required=False,
            ),
            OpenApiParameter(
                name='freshwater_station',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by freshwater station ID',
                required=False,
            ),
            # Feed property filters
            OpenApiParameter(
                name='feed__protein_percentage__gte',
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                description='Minimum protein percentage (0-100)',
                required=False,
            ),
            OpenApiParameter(
                name='feed__protein_percentage__lte',
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                description='Maximum protein percentage (0-100)',
                required=False,
            ),
            OpenApiParameter(
                name='feed__fat_percentage__gte',
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                description='Minimum fat percentage (0-100)',
                required=False,
            ),
            OpenApiParameter(
                name='feed__fat_percentage__lte',
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                description='Maximum fat percentage (0-100)',
                required=False,
            ),
            OpenApiParameter(
                name='feed__brand',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by exact brand name (case-insensitive)',
                required=False,
            ),
            OpenApiParameter(
                name='feed__brand__icontains',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by partial brand name (case-insensitive)',
                required=False,
            ),
            OpenApiParameter(
                name='feed__size_category',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by size category (MICRO, SMALL, MEDIUM, LARGE)',
                required=False,
            ),
            # Cost filters
            OpenApiParameter(
                name='feed_cost__gte',
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                description='Minimum feed cost per event',
                required=False,
            ),
            OpenApiParameter(
                name='feed_cost__lte',
                type=OpenApiTypes.DECIMAL,
                location=OpenApiParameter.QUERY,
                description='Maximum feed cost per event',
                required=False,
            ),
            # Feed type filters
            OpenApiParameter(
                name='feed',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by feed type ID',
                required=False,
            ),
            OpenApiParameter(
                name='feed__in',
                type={'type': 'array', 'items': {'type': 'integer'}},
                location=OpenApiParameter.QUERY,
                description='Filter by multiple feed type IDs (comma-separated)',
                required=False,
            ),
            # Report options
            OpenApiParameter(
                name='include_breakdowns',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Include dimensional breakdowns (default: true)',
                required=False,
            ),
            OpenApiParameter(
                name='include_time_series',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Include time series data (default: false)',
                required=False,
            ),
            OpenApiParameter(
                name='group_by',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Primary grouping for time series: 'day', 'week', or 'month'",
                required=False,
            ),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "object",
                        "properties": {
                            "total_feed_kg": {"type": "number"},
                            "total_feed_cost": {"type": "number"},
                            "events_count": {"type": "integer"},
                            "date_range": {
                                "type": "object",
                                "properties": {
                                    "start": {"type": "string", "format": "date"},
                                    "end": {"type": "string", "format": "date"}
                                }
                            }
                        }
                    },
                    "by_feed_type": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "feed_id": {"type": "integer"},
                                "feed_name": {"type": "string"},
                                "brand": {"type": "string"},
                                "protein_percentage": {"type": "number"},
                                "fat_percentage": {"type": "number"},
                                "total_kg": {"type": "number"},
                                "total_cost": {"type": "number"},
                                "events_count": {"type": "integer"}
                            }
                        }
                    },
                    "by_geography": {"type": "array"},
                    "by_area": {"type": "array"},
                    "by_container": {"type": "array"},
                    "time_series": {"type": "array"}
                }
            },
            400: {
                "type": "object",
                "properties": {
                    "error": {"type": "string"}
                }
            },
            500: {
                "type": "object",
                "properties": {
                    "error": {"type": "string"},
                    "detail": {"type": "string"}
                }
            }
        }
    )
    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(60))  # Cache for 1 minute
    def finance_report(self, request):
        """
        Comprehensive finance report with flexible filtering and breakdowns.
        
        Generates multi-dimensional analysis of feed usage and costs with support for:
        - Geographic filtering (geography, area, freshwater station)
        - Feed property filtering (protein %, fat %, brand)
        - Cost filtering
        - Time series analysis
        - Dimensional breakdowns
        
        Query parameters:
        - start_date (REQUIRED): Start of reporting period (YYYY-MM-DD)
        - end_date (REQUIRED): End of reporting period (YYYY-MM-DD)
        - include_breakdowns: Include dimensional breakdowns (default: true)
        - include_time_series: Include daily/weekly/monthly time series (default: false)
        - group_by: Time series grouping ('day', 'week', 'month')
        - Plus all FeedingEventFilter parameters (geography, area, feed properties, etc.)
        
        Returns:
            Comprehensive report with summary, breakdowns, and optional time series
        """
        # Validate required parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not (start_date and end_date):
            return Response(
                {"error": "Both start_date and end_date are required for finance reports"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate date format and range
        try:
            start = datetime.fromisoformat(start_date).date()
            end = datetime.fromisoformat(end_date).date()
            
            if start > end:
                return Response(
                    {"error": "start_date must be before or equal to end_date"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Apply all filters (geographic, nutritional, cost, etc.)
        queryset = self.filter_queryset(self.get_queryset())
        
        # Apply date range filter
        queryset = queryset.filter(feeding_date__range=(start, end))
        
        # Extract report options
        include_breakdowns = request.query_params.get('include_breakdowns', 'true').lower() == 'true'
        include_time_series = request.query_params.get('include_time_series', 'false').lower() == 'true'
        group_by = request.query_params.get('group_by')
        
        # Generate report using service
        try:
            report = FinanceReportingService.generate_finance_report(
                queryset=queryset,
                include_breakdowns=include_breakdowns,
                include_time_series=include_time_series,
                group_by=group_by
            )
            return Response(report)
        except Exception as e:
            logger.exception("Finance report generation failed")
            return Response(
                {
                    "error": "Report generation failed",
                    "detail": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
