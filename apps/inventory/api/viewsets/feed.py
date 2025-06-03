"""
Feed viewset for the inventory app.
"""
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.inventory.models import Feed
from apps.inventory.api.serializers.feed import FeedSerializer


class FeedViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Feed model.

    Provides CRUD operations for feed types used in aquaculture operations.
    """
    queryset = Feed.objects.all()
    serializer_class = FeedSerializer
    filter_backends = [
        DjangoFilterBackend, 
        filters.SearchFilter, 
        filters.OrderingFilter
    ]
    filterset_fields = ['is_active', 'brand']
    search_fields = ['name', 'brand', 'description']
    ordering_fields = ['name', 'brand', 'created_at']
    ordering = ['name']
