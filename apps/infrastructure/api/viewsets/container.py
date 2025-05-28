"""
Container viewset for the infrastructure app.

This module defines the viewset for the Container model.
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.infrastructure.models.container import Container
from apps.infrastructure.api.serializers.container import ContainerSerializer


class ContainerViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing Container instances."""
    
    queryset = Container.objects.all()
    serializer_class = ContainerSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'container_type', 'hall', 'area', 'active']
    search_fields = ['name', 'container_type__name', 'hall__name', 'area__name']
    ordering_fields = ['name', 'container_type__name', 'created_at']
    ordering = ['name']
