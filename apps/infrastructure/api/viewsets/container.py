"""
Container viewset for the infrastructure app.

This module defines the viewset for the Container model.
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.infrastructure.models.container import Container
from apps.infrastructure.api.serializers.container import ContainerSerializer
from rest_framework.authentication import TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from aquamind.utils.history_mixins import HistoryReasonMixin

class ContainerViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Containers within the aquaculture facility.

    Containers represent physical units (e.g., tanks, ponds, cages) used for
    holding aquatic organisms. They are associated with a specific container type,
    and can be located within a Hall and an Area. This endpoint allows for
    full CRUD operations on Container instances.

    **Filtering:**
    - `name`: Filter by the exact name of the container.
    - `container_type`: Filter by the ID of the ContainerType.
    - `hall`: Filter by the ID of the parent Hall.
    - `area`: Filter by the ID of the parent Area.
    - `active`: Filter by active status (boolean).

    **Searching:**
    - `name`: Search by container name (partial matches).
    - `container_type__name`: Search by the name of the ContainerType.
    - `hall__name`: Search by the name of the parent Hall.
    - `area__name`: Search by the name of the parent Area.

    **Ordering:**
    - `name` (default)
    - `container_type__name`
    - `created_at`
    """
    # Explicitly override authentication to prevent SessionAuthentication fallback
    authentication_classes = [TokenAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    queryset = Container.objects.all()
    serializer_class = ContainerSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'container_type', 'hall', 'area', 'active']
    search_fields = ['name', 'container_type__name', 'hall__name', 'area__name']
    ordering_fields = ['name', 'container_type__name', 'created_at']
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
