"""
ViewSets for the inventory app API.

These ViewSets provide the CRUD operations for feed and inventory-related models.
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import F, Q
from django.utils import timezone

from apps.inventory.models import Feed, FeedPurchase, FeedStock, FeedingEvent, BatchFeedingSummary, FeedRecommendation
from apps.inventory.services.feed_recommendation_service import FeedRecommendationService
from apps.inventory.serializers import (
    FeedSerializer,
    FeedPurchaseSerializer,
    FeedStockSerializer,
    FeedingEventSerializer,
    BatchFeedingSummarySerializer,
    BatchFeedingSummaryGenerateSerializer,
    FeedRecommendationSerializer,
    FeedRecommendationGenerateSerializer
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


class FeedRecommendationViewSet(viewsets.ModelViewSet):
    """ViewSet for FeedRecommendation model."""
    queryset = FeedRecommendation.objects.all()
    serializer_class = FeedRecommendationSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['batch_container_assignment', 'batch_container_assignment__batch', 
                      'batch_container_assignment__container', 'is_followed', 'recommended_date']
    search_fields = ['recommendation_reason']
    ordering_fields = ['recommended_date', 'created_at', 'recommended_feed_kg', 'expected_fcr']
    ordering = ['-recommended_date', '-created_at']

    @action(detail=False, methods=['get'])
    def by_container(self, request):
        """Get feed recommendations for a specific container."""
        container_id = request.query_params.get('container_id')
        if not container_id:
            return Response(
                {"error": "container_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        recommendations = self.get_queryset().filter(
            batch_container_assignment__container_id=container_id
        )
        serializer = self.get_serializer(recommendations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_batch(self, request):
        """Get feed recommendations for a specific batch."""
        batch_id = request.query_params.get('batch_id')
        if not batch_id:
            return Response(
                {"error": "batch_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        recommendations = self.get_queryset().filter(
            batch_container_assignment__batch_id=batch_id
        )
        serializer = self.get_serializer(recommendations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get feed recommendations for today."""
        today = timezone.now().date()
        recommendations = self.get_queryset().filter(recommended_date=today)
        serializer = self.get_serializer(recommendations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate feed recommendations for a container or batch."""
        serializer = FeedRecommendationGenerateSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                data = serializer.validated_data
                service = FeedRecommendationService()
                results = []
                
                # Generate recommendations based on the request
                if 'container' in data:
                    # Generate for a specific container
                    container = data['container']
                    date = data['date']
                    
                    # Find active batch container assignments for this container
                    from apps.batch.models import BatchContainerAssignment
                    assignments = BatchContainerAssignment.objects.filter(
                        container=container,
                        active=True
                    )
                    
                    for assignment in assignments:
                        recommendation = service.create_recommendation(assignment, date)
                        if recommendation:
                            results.append(recommendation)
                            
                elif 'batch' in data:
                    # Generate for all containers with this batch
                    batch = data['batch']
                    date = data['date']
                    
                    # Find active batch container assignments for this batch
                    from apps.batch.models import BatchContainerAssignment
                    assignments = BatchContainerAssignment.objects.filter(
                        batch=batch,
                        active=True,
                        container__feed_recommendations_enabled=True
                    )
                    
                    for assignment in assignments:
                        recommendation = service.create_recommendation(assignment, date)
                        if recommendation:
                            results.append(recommendation)
                
                if not results:
                    return Response(
                        {"message": "No recommendations could be generated. Check if containers have feed_recommendations_enabled=True and valid assignments."},
                        status=status.HTTP_404_NOT_FOUND
                    )
                    
                result_serializer = FeedRecommendationSerializer(results, many=True)
                return Response(result_serializer.data)
                
            except Exception as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def mark_followed(self, request, pk=None):
        """Mark a recommendation as followed."""
        recommendation = self.get_object()
        recommendation.is_followed = True
        recommendation.save()
        
        serializer = self.get_serializer(recommendation)
        return Response(serializer.data)
