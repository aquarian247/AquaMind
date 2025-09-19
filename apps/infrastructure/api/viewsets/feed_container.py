"""
FeedContainer viewset for the infrastructure app.

This module defines the viewset for the FeedContainer model.
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import FilterSet

from apps.infrastructure.models.feed_container import FeedContainer
from apps.infrastructure.api.serializers.feed_container import FeedContainerSerializer


class FeedContainerFilter(FilterSet):
    """Custom filterset for FeedContainer model to support __in lookups."""

    class Meta:
        model = FeedContainer
        fields = {
            'name': ['exact'],
            'container_type': ['exact', 'in'],
            'hall': ['exact', 'in'],
            'area': ['exact', 'in'],
            'active': ['exact']
        }

class FeedContainerViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Feed Containers within the aquaculture facility.

    Feed Containers represent physical units (e.g., silos, hoppers, bags) used for
    storing feed. They can be associated with a specific container type (defining
    its nature, e.g., "Silo - 10 Ton"), and can be located within a Hall and an Area.
    This endpoint allows for full CRUD operations on FeedContainer instances.

    **Filtering:**
    - `name`: Filter by the exact name of the feed container.
    - `container_type`: Filter by the ID of the feed container's type (e.g., Silo, Hopper).
    - `container_type__in`: Filter by multiple Container Type IDs (comma-separated).
    - `hall`: Filter by the ID of the parent Hall where the feed container is located.
    - `hall__in`: Filter by multiple Hall IDs (comma-separated).
    - `area`: Filter by the ID of the parent Area where the feed container is located.
    - `area__in`: Filter by multiple Area IDs (comma-separated).
    - `active`: Filter by active status (boolean).

    **Searching:**
    - `name`: Search by feed container name (partial matches).
    - `hall__name`: Search by the name of the parent Hall.
    - `area__name`: Search by the name of the parent Area.

    **Ordering:**
    - `name` (default)
    - `container_type`: Order by the type of the feed container.
    - `created_at`
    """
    
    queryset = FeedContainer.objects.all()
    serializer_class = FeedContainerSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = FeedContainerFilter
    search_fields = ['name', 'hall__name', 'area__name']
    ordering_fields = ['name', 'container_type', 'created_at']
    ordering = ['name']

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
