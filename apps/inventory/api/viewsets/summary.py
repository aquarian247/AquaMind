"""
Batch feeding summary viewset for the inventory app.
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.inventory.models import BatchFeedingSummary
from apps.inventory.api.serializers.summary import (
    BatchFeedingSummarySerializer, BatchFeedingSummaryGenerateSerializer
)


class BatchFeedingSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for BatchFeedingSummary model.

    Provides read operations for batch feeding summaries with generation
    capabilities.
    """
    queryset = BatchFeedingSummary.objects.all()
    serializer_class = BatchFeedingSummarySerializer
    filter_backends = [
        DjangoFilterBackend, 
        filters.OrderingFilter
    ]
    filterset_fields = ['batch', 'period_start', 'period_end']
    ordering_fields = [
        'period_start', 'period_end', 'total_feed_kg', 'feed_conversion_ratio'
    ]
    ordering = ['batch', '-period_end']

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        Generate a feeding summary for a batch over a specified period.
        """
        serializer = BatchFeedingSummaryGenerateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                summary = serializer.save()
                result_serializer = self.get_serializer(summary)
                return Response(result_serializer.data)
            except Exception as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def by_batch(self, request):
        """
        Get feeding summaries for a specific batch.
        """
        batch_id = request.query_params.get('batch_id')
        if not batch_id:
            return Response(
                {"error": "batch_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        summaries = self.get_queryset().filter(batch_id=batch_id)
        serializer = self.get_serializer(summaries, many=True)
        return Response(serializer.data)
