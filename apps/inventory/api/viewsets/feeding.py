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

from apps.inventory.models import FeedingEvent
from apps.inventory.api.serializers.feeding import FeedingEventSerializer
from aquamind.utils.history_mixins import HistoryReasonMixin


class FeedingEventViewSet(viewsets.ModelViewSet):
    """
    ViewSet for FeedingEvent model.

    Provides CRUD operations for feeding events with additional filtering
    capabilities.
    """
    queryset = FeedingEvent.objects.all()
    serializer_class = FeedingEventSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_fields = [
        'batch', 'feed', 'feeding_date', 'container', 'method'
    ]
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
    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(30))  # Cache for 30 seconds
    def summary(self, request):
        """
        Return aggregated statistics for feeding events.

        Optional query parameters
        ------------------------
        date      : 'today' (default) or specific ISO date (YYYY-MM-DD)
        batch     : Batch ID to filter by
        container : Container ID to filter by

        Response schema
        ----------------
        {
            "events_count": integer,
            "total_feed_kg": number
        }
        """
        # Base queryset
        qs = self.get_queryset()

        # --- Filter by date --------------------------------------------------
        date_param = request.query_params.get("date", "today")
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
