"""
Sensor viewset for the infrastructure app.

This module defines the viewset for the Sensor model.
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.infrastructure.models.sensor import Sensor
from apps.infrastructure.api.serializers.sensor import SensorSerializer


class SensorViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing Sensor instances."""
    
    queryset = Sensor.objects.all()
    serializer_class = SensorSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'sensor_type', 'container', 'active']
    search_fields = ['name', 'serial_number', 'manufacturer', 'container__name']
    ordering_fields = ['name', 'sensor_type', 'container__name', 'created_at']
    ordering = ['name']
