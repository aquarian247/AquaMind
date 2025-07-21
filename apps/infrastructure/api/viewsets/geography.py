"""
Geography viewset for the infrastructure app.

This module defines the viewset for the Geography model.
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.infrastructure.models.geography import Geography
from apps.infrastructure.api.serializers.geography import GeographySerializer
from rest_framework.authentication import TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated

class GeographyViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Geographical locations or zones.

    Geographies represent defined geographical areas relevant to the aquaculture
    operations, such as countries, regions, specific water bodies, or custom zones.
    These can be used to associate other entities (like facilities or environmental
    readings) with a spatial context.
    This endpoint allows for full CRUD operations on Geography instances.

    **Filtering:**
    - `name`: Filter by the exact name of the geography.

    **Searching:**
    - `name`: Search by geography name (partial matches).
    - `description`: Search within the description of the geography.

    **Ordering:**
    - `name` (default)
    - `created_at`
    """
    # Explicitly override authentication to prevent SessionAuthentication fallback
    authentication_classes = [TokenAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    queryset = Geography.objects.all()
    serializer_class = GeographySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
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
