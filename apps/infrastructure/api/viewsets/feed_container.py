"""
FeedContainer viewset for the infrastructure app.

This module defines the viewset for the FeedContainer model.
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.infrastructure.models.feed_container import FeedContainer
from apps.infrastructure.api.serializers.feed_container import FeedContainerSerializer


class FeedContainerViewSet(viewsets.ModelViewSet):
    """ViewSet for viewing and editing FeedContainer instances."""
    
    queryset = FeedContainer.objects.all()
    serializer_class = FeedContainerSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'container_type', 'hall', 'area', 'active']
    search_fields = ['name', 'hall__name', 'area__name']
    ordering_fields = ['name', 'container_type', 'created_at']
    ordering = ['name']
