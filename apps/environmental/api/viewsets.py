"""
ViewSets for the environmental app API.

These ViewSets provide the CRUD operations for environmental models,
with special handling for TimescaleDB hypertables.
"""
from rest_framework import viewsets, filters
from rest_framework.authentication import TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from aquamind.utils.history_mixins import HistoryReasonMixin
from django_filters import FilterSet
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg, Min, Max, Count
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import timedelta
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.environmental.models import (
    EnvironmentalParameter,
    EnvironmentalReading,
    PhotoperiodData,
    WeatherData,
    StageTransitionEnvironmental
)
from apps.environmental.api.serializers import (
    EnvironmentalParameterSerializer,
    EnvironmentalReadingSerializer,
    PhotoperiodDataSerializer,
    WeatherDataSerializer,
    StageTransitionEnvironmentalSerializer
)


class EnvironmentalParameterFilter(FilterSet):
    """Custom filterset for EnvironmentalParameter model."""

    class Meta:
        model = EnvironmentalParameter
        fields = {
            'name': ['exact', 'icontains'],
            'unit': ['exact']
        }


class EnvironmentalReadingFilter(FilterSet):
    """Custom filterset for EnvironmentalReading model to support __in lookups."""

    class Meta:
        model = EnvironmentalReading
        fields = {
            'parameter': ['exact', 'in'],
            'container': ['exact', 'in'],
            'batch': ['exact', 'in'],
            'sensor': ['exact', 'in'],
            'is_manual': ['exact']
        }


class PhotoperiodDataFilter(FilterSet):
    """Custom filterset for PhotoperiodData model to support __in lookups."""

    class Meta:
        model = PhotoperiodData
        fields = {
            'area': ['exact', 'in'],
            'date': ['exact'],
            'is_interpolated': ['exact']
        }


class WeatherDataFilter(FilterSet):
    """Custom filterset for WeatherData model to support __in lookups."""

    class Meta:
        model = WeatherData
        fields = {
            'area': ['exact', 'in']
        }


class EnvironmentalParameterViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing EnvironmentalParameter instances.
    
    Uses HistoryReasonMixin to automatically capture change reasons for audit trails.
    """
    
    # Explicitly override authentication to prevent SessionAuthentication fallback
    authentication_classes = [TokenAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    queryset = EnvironmentalParameter.objects.all()
    serializer_class = EnvironmentalParameterSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = EnvironmentalParameterFilter
    search_fields = ['name', 'description', 'unit']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class EnvironmentalReadingViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing EnvironmentalReading instances.
    
    Includes special filtering and aggregation methods for time-series data.
    Uses HistoryReasonMixin to automatically capture change reasons for audit trails.
    """
    
    # Explicitly override authentication to prevent SessionAuthentication fallback
    authentication_classes = [TokenAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    queryset = EnvironmentalReading.objects.select_related(
        'parameter', 'container', 'sensor', 'batch'
    )
    serializer_class = EnvironmentalReadingSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = EnvironmentalReadingFilter
    search_fields = ['notes', 'parameter__name', 'container__name']
    ordering_fields = ['reading_time', 'value', 'created_at']
    ordering = ['-reading_time']  # Default to most recent readings first
    
    def get_queryset(self):
        """
        Override to provide time-based filtering support.
        Supports from_time and to_time query parameters.
        Parses time strings into aware datetime objects for reliable filtering.
        Optimized with select_related to avoid N+1 queries.
        """
        queryset = super().get_queryset()

        from_time_str = self.request.query_params.get('from_time')
        to_time_str = self.request.query_params.get('to_time')

        # Early return if no time filters provided
        if not from_time_str and not to_time_str:
            return queryset

        # Apply time filters with error handling
        queryset = self._apply_time_filter(queryset, from_time_str, to_time_str)
        return queryset

    def _apply_time_filter(self, queryset, from_time_str, to_time_str):
        """Apply time-based filtering to queryset."""
        try:
            if from_time_str:
                from_time = self._parse_and_make_aware(from_time_str)
                if from_time:
                    queryset = queryset.filter(reading_time__gte=from_time)

            if to_time_str:
                to_time = self._parse_and_make_aware(to_time_str)
                if to_time:
                    queryset = queryset.filter(reading_time__lte=to_time)
        except ValueError:
            # Handle potential parsing errors gracefully
            pass

        return queryset

    def _parse_and_make_aware(self, time_str):
        """Parse datetime string and make it timezone aware if needed."""
        dt = parse_datetime(time_str)
        if dt and timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        Return the most recent readings for each parameter-container combo.
        
        Uses PostgreSQL DISTINCT ON when available, falls back to
        iteration for SQLite. Optimized with select_related to avoid N+1.
        """
        from django.db import connection
        
        # Use DISTINCT ON for PostgreSQL (optimal performance)
        if connection.vendor == 'postgresql':
            recent_readings = EnvironmentalReading.objects.select_related(
                'parameter', 'container', 'sensor', 'batch'
            ).order_by(
                'parameter', 'container', '-reading_time'
            ).distinct('parameter', 'container')
        else:
            # Fallback for SQLite/other databases
            recent_readings = []
            unique_pairs = EnvironmentalReading.objects.values(
                'parameter', 'container'
            ).distinct()
            
            for pair in unique_pairs:
                reading = EnvironmentalReading.objects.filter(
                    parameter=pair['parameter'],
                    container=pair['container']
                ).select_related(
                    'parameter', 'container', 'sensor', 'batch'
                ).order_by('-reading_time').first()
                if reading:
                    recent_readings.append(reading)
        
        serializer = self.get_serializer(recent_readings, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='container_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='ID of the container to fetch readings for.',
                required=True,
            ),
            OpenApiParameter(
                name='parameter_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter readings by environmental parameter.',
                required=False,
            ),
            OpenApiParameter(
                name='start_time',
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                description='Filter readings at or after this timestamp.',
                required=False,
            ),
            OpenApiParameter(
                name='end_time',
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                description='Filter readings at or before this timestamp.',
                required=False,
            ),
            OpenApiParameter(
                name='limit',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Maximum number of readings to return (default 1000).',
                required=False,
                default=1000,
            ),
        ]
    )
    @action(detail=False, methods=['get'])
    def by_container(self, request):
        """
        Get readings filtered by container and optional time range.
        
        Query parameters:
        - container_id: Required, container to fetch readings for
        - parameter_id: Optional, filter by specific parameter
        - start_time: Optional, ISO format datetime for range start
        - end_time: Optional, ISO format datetime for range end
        - limit: Optional, limit number of results (default: 1000)
        """
        from rest_framework import status as drf_status
        
        container_id = request.query_params.get('container_id')
        parameter_id = request.query_params.get('parameter_id')
        start_time = request.query_params.get('start_time')
        end_time = request.query_params.get('end_time')
        limit = int(request.query_params.get('limit', 1000))
        
        if not container_id:
            return Response(
                {"error": "container_id is required"},
                status=drf_status.HTTP_400_BAD_REQUEST
            )
            
        # Build query
        queryset = self.get_queryset().filter(container_id=container_id)
        
        if parameter_id:
            queryset = queryset.filter(parameter_id=parameter_id)
            
        if start_time:
            queryset = queryset.filter(reading_time__gte=start_time)
            
        if end_time:
            queryset = queryset.filter(reading_time__lte=end_time)
            
        queryset = queryset[:limit]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='group_by',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Aggregation dimension: parameter (default), container, or batch.',
                required=False,
                default='parameter',
            ),
            OpenApiParameter(
                name='days',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Number of days to include in the aggregation window.',
                required=False,
                default=7,
            ),
        ]
    )
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Return aggregated statistics for readings based on query parameters."""
        queryset = self.get_queryset()
        
        # Group by parameter by default
        group_by = request.query_params.get('group_by', 'parameter')
        
        # Define the time window for aggregation
        days = request.query_params.get('days', 7)
        try:
            days = int(days)
        except ValueError:
            days = 7
        
        from_time = timezone.now() - timedelta(days=days)
        queryset = queryset.filter(reading_time__gte=from_time)
        
        # Perform the aggregation
        if group_by == 'parameter':
            aggregation = queryset.values('parameter', 'parameter__name').annotate(
                avg_value=Avg('value'),
                min_value=Min('value'),
                max_value=Max('value'),
                count=Count('id')
            )
        elif group_by == 'container':
            aggregation = queryset.values('container', 'container__name').annotate(
                avg_value=Avg('value'),
                min_value=Min('value'),
                max_value=Max('value'),
                count=Count('id')
            )
        elif group_by == 'batch':
            aggregation = queryset.values('batch', 'batch__name').annotate(
                avg_value=Avg('value'),
                min_value=Min('value'),
                max_value=Max('value'),
                count=Count('id')
            )
        else:
            aggregation = queryset.values('parameter', 'parameter__name').annotate(
                avg_value=Avg('value'),
                min_value=Min('value'),
                max_value=Max('value'),
                count=Count('id')
            )
        
        return Response(aggregation)


class PhotoperiodDataViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing PhotoperiodData instances.
    
    Uses HistoryReasonMixin to automatically capture change reasons for audit trails.
    """
    
    # Explicitly override authentication to prevent SessionAuthentication fallback
    authentication_classes = [TokenAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    queryset = PhotoperiodData.objects.all()
    serializer_class = PhotoperiodDataSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PhotoperiodDataFilter
    search_fields = ['area__name']
    ordering_fields = ['date', 'day_length_hours', 'created_at']
    ordering = ['-date']  # Default to most recent dates first
    
    def get_queryset(self):
        """
        Override to provide date-range filtering support.
        Supports from_date and to_date query parameters.
        """
        queryset = super().get_queryset()
        
        from_date = self.request.query_params.get('from_date')
        to_date = self.request.query_params.get('to_date')
        
        if from_date:
            queryset = queryset.filter(date__gte=from_date)
        
        if to_date:
            queryset = queryset.filter(date__lte=to_date)
        
        return queryset


class WeatherDataViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing WeatherData instances.
    
    Includes special filtering and aggregation methods for time-series data.
    Uses HistoryReasonMixin to automatically capture change reasons for audit trails.
    """
    
    # Explicitly override authentication to prevent SessionAuthentication fallback
    authentication_classes = [TokenAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    queryset = WeatherData.objects.select_related('area')
    serializer_class = WeatherDataSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = WeatherDataFilter
    search_fields = ['area__name']
    ordering_fields = ['timestamp', 'created_at']
    ordering = ['-timestamp']  # Default to most recent timestamps first
    
    def get_queryset(self):
        """
        Override to provide time-based filtering support.
        Supports from_time and to_time query parameters.
        """
        queryset = super().get_queryset()
        
        from_time = self.request.query_params.get('from_time')
        to_time = self.request.query_params.get('to_time')
        
        if from_time:
            queryset = queryset.filter(timestamp__gte=from_time)
        
        if to_time:
            queryset = queryset.filter(timestamp__lte=to_time)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        Return the most recent weather data for each area.
        
        Uses PostgreSQL DISTINCT ON when available, falls back to
        iteration for SQLite. Optimized with select_related.
        """
        from django.db import connection
        
        # Use DISTINCT ON for PostgreSQL (optimal performance)
        if connection.vendor == 'postgresql':
            recent_data = WeatherData.objects.select_related(
                'area'
            ).order_by('area_id', '-timestamp').distinct('area_id')
        else:
            # Fallback for SQLite/other databases
            recent_data = []
            areas = WeatherData.objects.values('area').distinct()
            
            for area_dict in areas:
                data = WeatherData.objects.filter(
                    area=area_dict['area']
                ).select_related('area').order_by('-timestamp').first()
                if data:
                    recent_data.append(data)
        
        serializer = self.get_serializer(recent_data, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='area_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='ID of the area to fetch weather data for.',
                required=True,
            ),
            OpenApiParameter(
                name='start_time',
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                description='Filter weather data at or after this timestamp.',
                required=False,
            ),
            OpenApiParameter(
                name='end_time',
                type=OpenApiTypes.DATETIME,
                location=OpenApiParameter.QUERY,
                description='Filter weather data at or before this timestamp.',
                required=False,
            ),
            OpenApiParameter(
                name='limit',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Maximum number of records to return (default 1000).',
                required=False,
                default=1000,
            ),
        ]
    )
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
        from rest_framework import status as drf_status
        
        area_id = request.query_params.get('area_id')
        start_time = request.query_params.get('start_time')
        end_time = request.query_params.get('end_time')
        limit = int(request.query_params.get('limit', 1000))
        
        if not area_id:
            return Response(
                {"error": "area_id is required"},
                status=drf_status.HTTP_400_BAD_REQUEST
            )
            
        # Build query
        queryset = self.get_queryset().filter(area_id=area_id)
            
        if start_time:
            queryset = queryset.filter(timestamp__gte=start_time)
            
        if end_time:
            queryset = queryset.filter(timestamp__lte=end_time)
            
        queryset = queryset[:limit]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class StageTransitionEnvironmentalViewSet(HistoryReasonMixin, viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing StageTransitionEnvironmental instances.
    
    Uses HistoryReasonMixin to automatically capture change reasons for audit trails.
    """
    
    # Explicitly override authentication to prevent SessionAuthentication fallback
    authentication_classes = [TokenAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    queryset = StageTransitionEnvironmental.objects.all()
    serializer_class = StageTransitionEnvironmentalSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['batch_transfer']
    # Correct relationship paths: BatchTransfer has `source_batch` and `destination_batch`
    # (not plain `batch`).  Searching by batch number is more stable than by name.
    search_fields = [
        'notes',
        'batch_transfer__source_batch__batch_number',
        'batch_transfer__destination_batch__batch_number',
    ]
    ordering_fields = ['created_at']
    ordering = ['-created_at']  # Default to most recent first
