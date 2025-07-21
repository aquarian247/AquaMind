"""
FreshwaterStation viewset for the infrastructure app.

This module defines the viewset for the FreshwaterStation model.
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.infrastructure.models.station import FreshwaterStation
from apps.infrastructure.api.serializers.station import FreshwaterStationSerializer

class FreshwaterStationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Freshwater Stations.

    Freshwater Stations represent sources of freshwater for the aquaculture facility,
    such as wells, boreholes, or municipal supplies. They can be categorized by type
    and associated with a specific geographical location.
    This endpoint allows for full CRUD operations on FreshwaterStation instances.

    **Filtering:**
    - `name`: Filter by the exact name of the freshwater station.
    - `station_type`: Filter by the type of station (e.g., WELL, BOREHOLE, MUNICIPAL).
    - `geography`: Filter by the ID of the associated Geography.
    - `active`: Filter by active status (boolean).

    **Searching:**
    - `name`: Search by station name (partial matches).
    - `description`: Search within the description of the station.
    - `geography__name`: Search by the name of the associated Geography.

    **Ordering:**
    - `name` (default)
    - `station_type`
    - `geography__name`: Order by the name of the associated Geography.
    - `created_at`
    """
    
    queryset = FreshwaterStation.objects.all()
    serializer_class = FreshwaterStationSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'station_type', 'geography', 'active']
    search_fields = ['name', 'description', 'geography__name']
    ordering_fields = ['name', 'station_type', 'geography__name', 'created_at']
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
