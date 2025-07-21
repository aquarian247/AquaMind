"""
Hall viewset for the infrastructure app.

This module defines the viewset for the Hall model.
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.infrastructure.models.hall import Hall
from apps.infrastructure.api.serializers.hall import HallSerializer
from rest_framework.authentication import TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated

class HallViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Halls within the aquaculture facility.

    Halls represent distinct buildings or sections within the facility,
    often containing multiple containers or systems. They can be associated
    with a Freshwater Station.
    This endpoint allows for full CRUD operations on Hall instances.

    **Filtering:**
    - `name`: Filter by the exact name of the hall.
    - `freshwater_station`: Filter by the ID of the associated Freshwater Station.
    - `active`: Filter by active status (boolean).

    **Searching:**
    - `name`: Search by hall name (partial matches).
    - `description`: Search within the description of the hall.
    - `freshwater_station__name`: Search by the name of the associated Freshwater Station.

    **Ordering:**
    - `name` (default)
    - `freshwater_station__name`: Order by the name of the associated Freshwater Station.
    - `created_at`
    """
    # Explicitly override authentication to prevent SessionAuthentication fallback
    authentication_classes = [TokenAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    queryset = Hall.objects.all()
    serializer_class = HallSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'freshwater_station', 'active']
    search_fields = ['name', 'description', 'freshwater_station__name']
    ordering_fields = ['name', 'freshwater_station__name', 'created_at']
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
