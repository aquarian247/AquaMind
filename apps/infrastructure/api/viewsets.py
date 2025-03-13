"""
ViewSets for the infrastructure app API.

These ViewSets provide the CRUD operations for infrastructure models.
"""
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.infrastructure.models import (
    Geography,
    Area,
    FreshwaterStation,
    Hall,
    ContainerType,
    Container,
    Sensor,
    FeedContainer
)
from apps.infrastructure.api.serializers import (
    GeographySerializer,
    AreaSerializer,
    FreshwaterStationSerializer,
    HallSerializer,
    ContainerTypeSerializer,
    ContainerSerializer,
    SensorSerializer,
    FeedContainerSerializer
)


class GeographyViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing Geography instances."""
    
    queryset = Geography.objects.all()
    serializer_class = GeographySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class AreaViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing Area instances."""
    
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'geography', 'active']
    search_fields = ['name', 'geography__name']
    ordering_fields = ['name', 'geography__name', 'created_at']
    ordering = ['name']


class FreshwaterStationViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing FreshwaterStation instances."""
    
    queryset = FreshwaterStation.objects.all()
    serializer_class = FreshwaterStationSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'station_type', 'geography', 'active']
    search_fields = ['name', 'description', 'geography__name']
    ordering_fields = ['name', 'station_type', 'geography__name', 'created_at']
    ordering = ['name']


class HallViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing Hall instances."""
    
    queryset = Hall.objects.all()
    serializer_class = HallSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'freshwater_station', 'active']
    search_fields = ['name', 'description', 'freshwater_station__name']
    ordering_fields = ['name', 'freshwater_station__name', 'created_at']
    ordering = ['name']


class ContainerTypeViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing ContainerType instances."""
    
    queryset = ContainerType.objects.all()
    serializer_class = ContainerTypeSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'category']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'category', 'created_at']
    ordering = ['name']


class ContainerViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing Container instances."""
    
    queryset = Container.objects.all()
    serializer_class = ContainerSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'container_type', 'hall', 'area', 'active']
    search_fields = ['name', 'container_type__name', 'hall__name', 'area__name']
    ordering_fields = ['name', 'container_type__name', 'created_at']
    ordering = ['name']


class SensorViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing Sensor instances."""
    
    queryset = Sensor.objects.all()
    serializer_class = SensorSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'sensor_type', 'container', 'active']
    search_fields = ['name', 'serial_number', 'manufacturer', 'container__name']
    ordering_fields = ['name', 'sensor_type', 'container__name', 'created_at']
    ordering = ['name']


class FeedContainerViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing FeedContainer instances."""
    
    queryset = FeedContainer.objects.all()
    serializer_class = FeedContainerSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'container_type', 'hall', 'area', 'active']
    search_fields = ['name', 'hall__name', 'area__name']
    ordering_fields = ['name', 'container_type', 'created_at']
    ordering = ['name']
