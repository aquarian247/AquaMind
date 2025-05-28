"""
Area viewset for the infrastructure app.

This module defines the viewset for the Area model.
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.infrastructure.models.area import Area
from apps.infrastructure.api.serializers.area import AreaSerializer


class AreaViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing Area instances."""
    
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'geography', 'active']
    search_fields = ['name', 'geography__name']
    ordering_fields = ['name', 'geography__name', 'created_at']
    ordering = ['name']
