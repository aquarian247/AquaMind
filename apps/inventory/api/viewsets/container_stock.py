"""
Feed Container Stock viewsets for inventory management.

This module defines viewsets for FeedContainerStock model,
supporting FIFO inventory tracking operations.
"""

from decimal import Decimal
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.db.models import Sum, Count, Q

from aquamind.utils.history_mixins import HistoryReasonMixin

from apps.inventory.models import FeedContainerStock
from apps.inventory.api.serializers import (
    FeedContainerStockSerializer,
    FeedContainerStockCreateSerializer
)
from apps.inventory.services import FIFOInventoryService


class FeedContainerStockViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """
    API endpoint for managing Feed Container Stock.
    
    Provides CRUD operations for feed container stock entries,
    supporting FIFO inventory tracking. Uses HistoryReasonMixin to capture
    audit change reasons.
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
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='feed_container_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by specific feed container ID',
                required=False,
            ),
            OpenApiParameter(
                name='feed_type_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by specific feed type ID',
                required=False,
            ),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "total_quantity_kg": {"type": "number", "description": "Total feed quantity in kg"},
                    "total_value": {"type": "number", "description": "Total value of feed stock"},
                    "unique_feed_types": {"type": "integer", "description": "Number of different feed types in stock"},
                    "unique_containers": {"type": "integer", "description": "Number of containers with stock"},
                    "by_feed_type": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "feed_id": {"type": "integer"},
                                "feed_name": {"type": "string"},
                                "total_quantity_kg": {"type": "number"},
                                "total_value": {"type": "number"},
                                "container_count": {"type": "integer"}
                            }
                        }
                    },
                    "by_container": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "container_id": {"type": "integer"},
                                "container_name": {"type": "string"},
                                "total_quantity_kg": {"type": "number"},
                                "total_value": {"type": "number"},
                                "feed_type_count": {"type": "integer"}
                            }
                        }
                    }
                }
            }
        }
    )
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get comprehensive stock summary with aggregations.
        
        Provides:
        - Total quantity and value across all stock
        - Breakdown by feed type
        - Breakdown by container
        
        Query parameters:
        - feed_container_id: Filter by specific container
        - feed_type_id: Filter by specific feed type
        """
        queryset = self.get_queryset().filter(quantity_kg__gt=0)
        
        # Apply filters
        feed_container_id = request.query_params.get('feed_container_id')
        if feed_container_id:
            queryset = queryset.filter(feed_container_id=feed_container_id)
        
        feed_type_id = request.query_params.get('feed_type_id')
        if feed_type_id:
            queryset = queryset.filter(feed_purchase__feed_id=feed_type_id)
        
        # Overall aggregates
        overall = queryset.aggregate(
            total_quantity=Sum('quantity_kg')
        )
        
        total_quantity = overall['total_quantity'] or Decimal('0')
        
        # Calculate total value
        total_value = Decimal('0')
        for stock in queryset.select_related('feed_purchase'):
            total_value += stock.quantity_kg * stock.feed_purchase.cost_per_kg
        
        # Count unique feed types and containers
        unique_feed_types = queryset.values('feed_purchase__feed').distinct().count()
        unique_containers = queryset.values('feed_container').distinct().count()
        
        # Aggregate by feed type
        by_feed_type = {}
        for stock in queryset.select_related('feed_purchase__feed'):
            feed_id = stock.feed_purchase.feed.id
            feed_name = stock.feed_purchase.feed.name
            
            if feed_id not in by_feed_type:
                by_feed_type[feed_id] = {
                    'feed_id': feed_id,
                    'feed_name': feed_name,
                    'total_quantity_kg': Decimal('0'),
                    'total_value': Decimal('0'),
                    'containers': set()
                }
            
            by_feed_type[feed_id]['total_quantity_kg'] += stock.quantity_kg
            by_feed_type[feed_id]['total_value'] += (
                stock.quantity_kg * stock.feed_purchase.cost_per_kg
            )
            by_feed_type[feed_id]['containers'].add(stock.feed_container_id)
        
        # Convert to list and add container count
        feed_type_summary = []
        for feed_data in by_feed_type.values():
            feed_type_summary.append({
                'feed_id': feed_data['feed_id'],
                'feed_name': feed_data['feed_name'],
                'total_quantity_kg': float(feed_data['total_quantity_kg']),
                'total_value': float(feed_data['total_value']),
                'container_count': len(feed_data['containers'])
            })
        
        # Aggregate by container
        by_container = {}
        for stock in queryset.select_related('feed_container', 'feed_purchase'):
            container_id = stock.feed_container.id
            container_name = stock.feed_container.name
            
            if container_id not in by_container:
                by_container[container_id] = {
                    'container_id': container_id,
                    'container_name': container_name,
                    'total_quantity_kg': Decimal('0'),
                    'total_value': Decimal('0'),
                    'feed_types': set()
                }
            
            by_container[container_id]['total_quantity_kg'] += stock.quantity_kg
            by_container[container_id]['total_value'] += (
                stock.quantity_kg * stock.feed_purchase.cost_per_kg
            )
            by_container[container_id]['feed_types'].add(stock.feed_purchase.feed_id)
        
        # Convert to list and add feed type count
        container_summary = []
        for container_data in by_container.values():
            container_summary.append({
                'container_id': container_data['container_id'],
                'container_name': container_data['container_name'],
                'total_quantity_kg': float(container_data['total_quantity_kg']),
                'total_value': float(container_data['total_value']),
                'feed_type_count': len(container_data['feed_types'])
            })
        
        return Response({
            'total_quantity_kg': float(total_quantity),
            'total_value': float(total_value),
            'unique_feed_types': unique_feed_types,
            'unique_containers': unique_containers,
            'by_feed_type': feed_type_summary,
            'by_container': container_summary
        }) 