from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q

from .models import (
    EnvironmentalParameter,
    EnvironmentalReading,
    PhotoperiodData,
    WeatherData,
    StageTransitionEnvironmental
)
from .serializers import (
    EnvironmentalParameterSerializer,
    EnvironmentalReadingSerializer,
    EnvironmentalReadingCreateSerializer,
    PhotoperiodDataSerializer,
    WeatherDataSerializer,
    WeatherDataCreateSerializer,
    StageTransitionEnvironmentalSerializer
)


class EnvironmentalParameterViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing environmental parameters.
    
    Provides CRUD operations for parameters that can be monitored in the system,
    such as temperature, oxygen, pH, salinity, etc.
    """
    queryset = EnvironmentalParameter.objects.all().order_by('name')
    serializer_class = EnvironmentalParameterSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'unit']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'unit', 'created_at']


class EnvironmentalReadingViewSet(viewsets.ModelViewSet):
    """
    API endpoint for environmental readings.
    
    Provides CRUD operations for time-series environmental data records.
    Uses TimescaleDB hypertable for efficient storage and querying of time-series data.
    """
    queryset = EnvironmentalReading.objects.all().order_by('-reading_time')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['parameter', 'container', 'batch', 'sensor', 'is_manual', 'reading_time']
    search_fields = ['notes']
    ordering_fields = ['reading_time', 'value', 'created_at']
    
    def get_serializer_class(self):
        """
        Return different serializers for list/retrieve vs create/update operations.
        
        This provides better performance by using a simpler serializer for create operations,
        while providing detailed nested data for retrieve operations.
        """
        if self.action in ['create', 'update', 'partial_update']:
            return EnvironmentalReadingCreateSerializer
        return EnvironmentalReadingSerializer
    
    @action(detail=False, methods=['get'])
    def by_container(self, request):
        """
        Get readings filtered by container and optional time range.
        
        Query parameters:
        - container_id: Required, the ID of the container to fetch readings for
        - parameter_id: Optional, filter by specific parameter
        - start_time: Optional, ISO format datetime for range start
        - end_time: Optional, ISO format datetime for range end
        - limit: Optional, limit number of results (default: 1000)
        """
        container_id = request.query_params.get('container_id')
        parameter_id = request.query_params.get('parameter_id')
        start_time = request.query_params.get('start_time')
        end_time = request.query_params.get('end_time')
        limit = int(request.query_params.get('limit', 1000))
        
        if not container_id:
            return Response(
                {"error": "container_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Build query
        queryset = self.queryset.filter(container_id=container_id)
        
        if parameter_id:
            queryset = queryset.filter(parameter_id=parameter_id)
            
        if start_time:
            queryset = queryset.filter(reading_time__gte=start_time)
            
        if end_time:
            queryset = queryset.filter(reading_time__lte=end_time)
            
        queryset = queryset[:limit]
        serializer = EnvironmentalReadingSerializer(queryset, many=True)
        return Response(serializer.data)


class PhotoperiodDataViewSet(viewsets.ModelViewSet):
    """
    API endpoint for photoperiod data.
    
    Provides CRUD operations for photoperiod data records, which store
    day length and light intensity information for areas.
    """
    queryset = PhotoperiodData.objects.all().order_by('-date')
    serializer_class = PhotoperiodDataSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['area', 'date', 'is_interpolated']
    ordering_fields = ['date', 'day_length_hours', 'light_intensity']


class WeatherDataViewSet(viewsets.ModelViewSet):
    """
    API endpoint for weather data.
    
    Provides CRUD operations for weather condition records.
    Uses TimescaleDB hypertable for efficient storage and querying of time-series data.
    """
    queryset = WeatherData.objects.all().order_by('-timestamp')
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['area', 'timestamp']
    ordering_fields = ['timestamp', 'temperature', 'wind_speed', 'precipitation']
    
    def get_serializer_class(self):
        """
        Return different serializers for list/retrieve vs create/update operations.
        """
        if self.action in ['create', 'update', 'partial_update']:
            return WeatherDataCreateSerializer
        return WeatherDataSerializer
    
    @action(detail=False, methods=['get'])
    def by_area(self, request):
        """
        Get weather data filtered by area and optional time range.
        
        Query parameters:
        - area_id: Required, the ID of the area to fetch weather data for
        - start_time: Optional, ISO format datetime for range start
        - end_time: Optional, ISO format datetime for range end
        - limit: Optional, limit number of results (default: 1000)
        """
        area_id = request.query_params.get('area_id')
        start_time = request.query_params.get('start_time')
        end_time = request.query_params.get('end_time')
        limit = int(request.query_params.get('limit', 1000))
        
        if not area_id:
            return Response(
                {"error": "area_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Build query
        queryset = self.queryset.filter(area_id=area_id)
            
        if start_time:
            queryset = queryset.filter(timestamp__gte=start_time)
            
        if end_time:
            queryset = queryset.filter(timestamp__lte=end_time)
            
        queryset = queryset[:limit]
        serializer = WeatherDataSerializer(queryset, many=True)
        return Response(serializer.data)


class StageTransitionEnvironmentalViewSet(viewsets.ModelViewSet):
    """
    API endpoint for stage transition environmental conditions.
    
    Provides CRUD operations for environmental conditions recorded during
    batch transfers between containers or lifecycle stages.
    """
    queryset = StageTransitionEnvironmental.objects.all().order_by('-created_at')
    serializer_class = StageTransitionEnvironmentalSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['batch_transfer']
    search_fields = ['notes']