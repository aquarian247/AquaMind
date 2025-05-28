"""
Geography viewset for the infrastructure app.

This module defines the viewset for the Geography model.
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.infrastructure.models.geography import Geography
from apps.infrastructure.api.serializers.geography import GeographySerializer


class GeographyViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing Geography instances."""
    
    queryset = Geography.objects.all()
    serializer_class = GeographySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
