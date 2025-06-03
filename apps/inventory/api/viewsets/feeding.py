"""
Feeding event viewset for the inventory app.
"""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.inventory.models import FeedingEvent
from apps.inventory.api.serializers.feeding import FeedingEventSerializer


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
