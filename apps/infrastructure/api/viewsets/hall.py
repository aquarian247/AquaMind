"""
Hall viewset for the infrastructure app.

This module defines the viewset for the Hall model.
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.infrastructure.models.hall import Hall
from apps.infrastructure.api.serializers.hall import HallSerializer


class HallViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing Hall instances."""
    
    queryset = Hall.objects.all()
    serializer_class = HallSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'freshwater_station', 'active']
    search_fields = ['name', 'description', 'freshwater_station__name']
    ordering_fields = ['name', 'freshwater_station__name', 'created_at']
    ordering = ['name']
