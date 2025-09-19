"""
Feeding event viewset for the inventory app.
"""
from rest_framework import viewsets, filters, status
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
from aquamind.utils.history_mixins import HistoryReasonMixin


class FeedingEventViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Feeding Events in aquaculture operations.

    Feeding events record the amount of feed given to batches in specific containers
    on particular dates. This endpoint provides full CRUD operations for feeding events.

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
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_class = FeedingEventFilter
    search_fields = ['notes']
    ordering_fields = ['feeding_date', 'feeding_time', 'amount_kg']
    ordering = ['-feeding_date', '-feeding_time']

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
                },
                "required": ["events_count", "total_feed_kg"],
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
            "total_feed_kg": number
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
        )

        return Response(
            {
                "events_count": aggregates["events_count"] or 0,
                "total_feed_kg": float(aggregates["total_feed_kg"] or 0),
            }
        )
