"""
ContainerType viewset for the infrastructure app.

This module defines the viewset for the ContainerType model.
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.infrastructure.models.container_type import ContainerType
from apps.infrastructure.api.serializers.container_type import ContainerTypeSerializer

class ContainerTypeViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Container Types.

    Container Types define the characteristics and categories of different containers
    used in the aquaculture facility (e.g., "Circular Tank - 5000L", "Rectangular Pond - 1 Ha").
    This endpoint allows for full CRUD operations on ContainerType instances.

    **Filtering:**
    - `name`: Filter by the exact name of the container type.
    - `category`: Filter by the category of the container type (e.g., TANK, POND, CAGE).

    **Searching:**
    - `name`: Search by container type name (partial matches).
    - `description`: Search within the description of the container type.

    **Ordering:**
    - `name` (default)
    - `category`
    - `created_at`
    """
    
    queryset = ContainerType.objects.all()
    serializer_class = ContainerTypeSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'category']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'category', 'created_at']
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
