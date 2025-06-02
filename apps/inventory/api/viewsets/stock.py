"""
Feed stock viewset for the inventory app.
"""
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import F

from apps.inventory.models import FeedStock
from apps.inventory.api.serializers.stock import FeedStockSerializer


class FeedStockViewSet(viewsets.ModelViewSet):
    """
    ViewSet for FeedStock model.
    
    Provides CRUD operations for feed stock levels in feed containers.
    """
    queryset = FeedStock.objects.all()
    serializer_class = FeedStockSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['feed', 'feed_container']
    ordering_fields = ['current_quantity_kg', 'last_updated']
    ordering = ['feed__brand', 'feed__name']

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """
        Return feed stocks that are below reorder threshold.
        """
        low_stocks = self.get_queryset().filter(
            current_quantity_kg__lte=F('reorder_threshold_kg')
        )
        serializer = self.get_serializer(low_stocks, many=True)
        return Response(serializer.data)
