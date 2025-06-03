from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import F
from django.utils import timezone

from .models import (
    Feed, FeedPurchase, FeedStock, FeedingEvent, 
    BatchFeedingSummary
)
# Feed recommendation service has been deprecated and removed
from .serializers import (
    FeedSerializer,
    FeedPurchaseSerializer,
    FeedStockSerializer,
    FeedingEventSerializer,
    BatchFeedingSummarySerializer,
    BatchFeedingSummaryGenerateSerializer
    # FeedRecommendation serializers have been deprecated and removed
)


class FeedViewSet(viewsets.ModelViewSet):
    """ViewSet for Feed model."""
    queryset = Feed.objects.all()
    serializer_class = FeedSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['size_category', 'is_active', 'brand']
    search_fields = ['name', 'brand', 'description']
    ordering_fields = ['name', 'brand', 'created_at']
    ordering = ['brand', 'name']


class FeedPurchaseViewSet(viewsets.ModelViewSet):
    """ViewSet for FeedPurchase model."""
    queryset = FeedPurchase.objects.all()
    serializer_class = FeedPurchaseSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['feed', 'supplier', 'purchase_date']
    search_fields = ['supplier', 'batch_number', 'notes']
    ordering_fields = ['purchase_date', 'quantity_kg', 'cost_per_kg']
    ordering = ['-purchase_date']


class FeedStockViewSet(viewsets.ModelViewSet):
    """ViewSet for FeedStock model."""
    queryset = FeedStock.objects.all()
    serializer_class = FeedStockSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['feed', 'feed_container']
    ordering_fields = ['current_quantity_kg', 'last_updated']
    ordering = ['feed__brand', 'feed__name']

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Return feed stocks that are below reorder threshold."""
        low_stocks = self.get_queryset().filter(
            current_quantity_kg__lte=F('reorder_threshold_kg')
        )
        serializer = self.get_serializer(low_stocks, many=True)
        return Response(serializer.data)


class FeedingEventViewSet(viewsets.ModelViewSet):
    """ViewSet for FeedingEvent model."""
    queryset = FeedingEvent.objects.all()
    serializer_class = FeedingEventSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['batch', 'feed', 'feeding_date', 'container', 'method']
    search_fields = ['notes']
    ordering_fields = ['feeding_date', 'feeding_time', 'amount_kg']
    ordering = ['-feeding_date', '-feeding_time']

    @action(detail=False, methods=['get'])
    def by_batch(self, request):
        """Get feeding events for a specific batch."""
        batch_id = request.query_params.get('batch_id')
        if not batch_id:
            return Response(
                {"error": "batch_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        feeding_events = self.get_queryset().filter(batch_id=batch_id)
        serializer = self.get_serializer(feeding_events, many=True)
        return Response(serializer.data)


class BatchFeedingSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for BatchFeedingSummary model."""
    queryset = BatchFeedingSummary.objects.all()
    serializer_class = BatchFeedingSummarySerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['batch', 'period_start', 'period_end']
    ordering_fields = ['period_start', 'period_end', 'total_feed_kg', 'feed_conversion_ratio']
    ordering = ['batch', '-period_end']

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate a feeding summary for a batch over a specified period."""
        serializer = BatchFeedingSummaryGenerateSerializer(data=request.data)

        if serializer.is_valid():
            try:
                summary = serializer.save()
                result_serializer = BatchFeedingSummarySerializer(summary)
                return Response(result_serializer.data)
            except Exception as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def by_batch(self, request):
        """Get feeding summaries for a specific batch."""
        batch_id = request.query_params.get('batch_id')
        if not batch_id:
            return Response(
                {"error": "batch_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        summaries = self.get_queryset().filter(batch_id=batch_id)
        serializer = self.get_serializer(summaries, many=True)
        return Response(serializer.data)


# FeedRecommendationViewSet has been deprecated and removed as part of the refactoring
# to improve code quality and maintainability. The feed recommendation feature
# has been completely removed from the application.