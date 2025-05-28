"""
ContainerType viewset for the infrastructure app.

This module defines the viewset for the ContainerType model.
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.infrastructure.models.container_type import ContainerType
from apps.infrastructure.api.serializers.container_type import ContainerTypeSerializer


class ContainerTypeViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing ContainerType instances."""
    
    queryset = ContainerType.objects.all()
    serializer_class = ContainerTypeSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'category']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'category', 'created_at']
    ordering = ['name']
