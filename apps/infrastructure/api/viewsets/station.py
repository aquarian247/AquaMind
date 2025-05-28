"""
FreshwaterStation viewset for the infrastructure app.

This module defines the viewset for the FreshwaterStation model.
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.infrastructure.models.station import FreshwaterStation
from apps.infrastructure.api.serializers.station import FreshwaterStationSerializer


class FreshwaterStationViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing FreshwaterStation instances."""
    
    queryset = FreshwaterStation.objects.all()
    serializer_class = FreshwaterStationSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'station_type', 'geography', 'active']
    search_fields = ['name', 'description', 'geography__name']
    ordering_fields = ['name', 'station_type', 'geography__name', 'created_at']
    ordering = ['name']
