"""
Area viewset for the infrastructure app.

This module defines the viewset for the Area model.
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.infrastructure.models.area import Area
from apps.infrastructure.api.serializers.area import AreaSerializer
from rest_framework.authentication import TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated

class AreaViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Areas within the aquaculture facility.

    Areas represent distinct geographical or functional zones within a larger geography
    (e.g., a specific section of a farm). This endpoint allows for full CRUD operations
    on Area instances.

    **Filtering:**
    - `name`: Filter by the exact name of the area.
    - `geography`: Filter by the ID of the parent Geography.
    - `active`: Filter by active status (boolean).

    **Searching:**
    - `name`: Search by area name (partial matches).
    - `geography__name`: Search by the name of the parent Geography (partial matches).

    **Ordering:**
    - `name` (default)
    - `geography__name`
    - `created_at`
    """
    # Explicitly override authentication to prevent SessionAuthentication fallback
    authentication_classes = [TokenAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'geography', 'active']
    search_fields = ['name', 'geography__name']
    ordering_fields = ['name', 'geography__name', 'created_at']
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
