"""
ViewSets for the environmental app API.

These ViewSets provide the CRUD operations for environmental models,
with special handling for TimescaleDB hypertables.
"""
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg, Min, Max, Count
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import timedelta

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


class EnvironmentalParameterViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing EnvironmentalParameter instances."""
    
    queryset = EnvironmentalParameter.objects.all()
    serializer_class = EnvironmentalParameterSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'unit']
    search_fields = ['name', 'description', 'unit']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class EnvironmentalReadingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing EnvironmentalReading instances.
    
    Includes special filtering and aggregation methods for time-series data.
    """
    
    queryset = EnvironmentalReading.objects.all()
    serializer_class = EnvironmentalReadingSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['parameter', 'container', 'batch', 'sensor', 'is_manual']
    search_fields = ['notes', 'parameter__name', 'container__name']
    ordering_fields = ['reading_time', 'value', 'created_at']
    ordering = ['-reading_time']  # Default to most recent readings first
    
    def get_queryset(self):
        """
        Override to provide time-based filtering support.
        Supports from_time and to_time query parameters.
        Parses time strings into aware datetime objects for reliable filtering.
        """
        queryset = super().get_queryset()
        
        from_time_str = self.request.query_params.get('from_time')
        to_time_str = self.request.query_params.get('to_time')
        
        try:
            if from_time_str:
                from_time = parse_datetime(from_time_str)
                if from_time and timezone.is_naive(from_time):
                    # Attempt to make naive datetime aware using the current timezone
                    # Adjust this logic if a specific timezone is expected from the client
                    from_time = timezone.make_aware(from_time, timezone.get_current_timezone())
                if from_time:
                    queryset = queryset.filter(reading_time__gte=from_time)

            if to_time_str:
                to_time = parse_datetime(to_time_str)
                if to_time and timezone.is_naive(to_time):
                    # Attempt to make naive datetime aware using the current timezone
                    to_time = timezone.make_aware(to_time, timezone.get_current_timezone())
                if to_time:
                    queryset = queryset.filter(reading_time__lte=to_time)
        except ValueError: 
            # Handle potential parsing errors gracefully, maybe log or ignore
            pass # Or raise ParseError("Invalid datetime format")

        return queryset
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Return the most recent readings for each parameter-container combination."""
        # Get most recent readings for each unique parameter-container combination
        # This leverages TimescaleDB's efficient time-based indexing
        
        # Subquery would be ideal here, but for simplicity:
        recent_readings = []
        
        # Get unique parameter-container combinations
        param_container_pairs = EnvironmentalReading.objects.values('parameter', 'container').distinct()
        
        for pair in param_container_pairs:
            # For each combination, get the most recent reading
            reading = EnvironmentalReading.objects.filter(
                parameter=pair['parameter'],
                container=pair['container']
            ).order_by('-reading_time').first()
            
            if reading:
                recent_readings.append(reading)
        
        serializer = self.get_serializer(recent_readings, many=True)
        return Response(serializer.data)
    
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


class PhotoperiodDataViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing PhotoperiodData instances."""
    
    queryset = PhotoperiodData.objects.all()
    serializer_class = PhotoperiodDataSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['area', 'date', 'is_interpolated']
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


class WeatherDataViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing WeatherData instances.
    
    Includes special filtering and aggregation methods for time-series data.
    """
    
    queryset = WeatherData.objects.all()
    serializer_class = WeatherDataSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['area']
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
        """Return the most recent weather data for each area."""
        recent_data = []
        
        # Get unique areas
        areas = WeatherData.objects.values('area').distinct()
        
        for area_dict in areas:
            # For each area, get the most recent weather data
            data = WeatherData.objects.filter(
                area=area_dict['area']
            ).order_by('-timestamp').first()
            
            if data:
                recent_data.append(data)
        
        serializer = self.get_serializer(recent_data, many=True)
        return Response(serializer.data)


class StageTransitionEnvironmentalViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing StageTransitionEnvironmental instances."""
    
    queryset = StageTransitionEnvironmental.objects.all()
    serializer_class = StageTransitionEnvironmentalSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['batch_transfer']
    search_fields = ['notes', 'batch_transfer__batch__name']
    ordering_fields = ['created_at']
    ordering = ['-created_at']  # Default to most recent first
