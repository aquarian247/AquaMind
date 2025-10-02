"""
Feed Container Stock viewsets for inventory management.

This module defines viewsets for FeedContainerStock model,
supporting FIFO inventory tracking operations.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.inventory.models import FeedContainerStock
from apps.inventory.api.serializers import (
    FeedContainerStockSerializer,
    FeedContainerStockCreateSerializer
)
from apps.inventory.services import FIFOInventoryService


class FeedContainerStockViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Feed Container Stock.
    
    Provides CRUD operations for feed container stock entries,
    supporting FIFO inventory tracking.
    """
    queryset = FeedContainerStock.objects.select_related(
        'feed_container', 'feed_purchase', 'feed_purchase__feed'
    ).all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    
    # Filtering options
    filterset_fields = {
        'feed_container': ['exact'],
        'feed_purchase': ['exact'],
        'entry_date': ['exact', 'gte', 'lte'],
        'quantity_kg': ['exact', 'gte', 'lte'],
    }
    search_fields = [
        'feed_container__name',
        'feed_purchase__batch_number',
        'feed_purchase__feed__name'
    ]
    ordering_fields = ['entry_date', 'quantity_kg', 'created_at']
    ordering = ['entry_date']  # FIFO order by default
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return FeedContainerStockCreateSerializer
        return FeedContainerStockSerializer
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='container_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Limit results to a specific feed container.',
                required=False,
            ),
        ]
    )
    @action(detail=False, methods=['get'])
    def by_container(self, request):
        """
        Get feed container stock grouped by container.
        
        Query parameters:
        - container_id: Filter by specific container
        """
        container_id = request.query_params.get('container_id')
        queryset = self.get_queryset()
        
        if container_id:
            queryset = queryset.filter(feed_container_id=container_id)
        
        # Group by container
        containers = {}
        for stock in queryset:
            container_name = stock.feed_container.name
            if container_name not in containers:
                containers[container_name] = {
                    'container_id': stock.feed_container.id,
                    'container_name': container_name,
                    'stock_entries': []
                }
            
            serializer = FeedContainerStockSerializer(stock)
            containers[container_name]['stock_entries'].append(serializer.data)
        
        return Response(list(containers.values()))
    
    @action(detail=False, methods=['post'])
    def add_to_container(self, request):
        """
        Add feed batch to container using FIFO service.
        
        Expected payload:
        {
            "feed_container_id": 1,
            "feed_purchase_id": 2,
            "quantity_kg": "100.00"
        }
        """
        serializer = FeedContainerStockCreateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Use FIFO service to add feed to container
                stock_entry = FIFOInventoryService.add_feed_to_container(
                    feed_container=serializer.validated_data['feed_container'],
                    feed_purchase=serializer.validated_data['feed_purchase'],
                    quantity_kg=serializer.validated_data['quantity_kg'],
                    entry_date=serializer.validated_data.get('entry_date')
                )
                
                response_serializer = FeedContainerStockSerializer(stock_entry)
                return Response(
                    response_serializer.data,
                    status=status.HTTP_201_CREATED
                )
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='container_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='ID of the feed container to fetch FIFO ordered stock for.',
                required=True,
            ),
        ]
    )
    @action(detail=False, methods=['get'])
    def fifo_order(self, request):
        """
        Get feed container stock in FIFO order for a specific container.
        
        Query parameters:
        - container_id: Required. Container to get FIFO order for.
        """
        container_id = request.query_params.get('container_id')
        if not container_id:
            return Response(
                {'error': 'container_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            fifo_stock = FIFOInventoryService.get_container_stock_fifo_order(
                container_id=int(container_id)
            )
            
            serializer = FeedContainerStockSerializer(fifo_stock, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            ) 