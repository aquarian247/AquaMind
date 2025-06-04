"""
FreshwaterStation viewset for the infrastructure app.

This module defines the viewset for the FreshwaterStation model.
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

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

    @swagger_auto_schema(
        operation_summary="List Freshwater Stations",
        operation_description="Retrieves a list of all freshwater stations, with support for filtering, searching, and ordering.",
        responses={
            200: FreshwaterStationSerializer(many=True),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create Freshwater Station",
        operation_description="Creates a new freshwater station.",
        request_body=FreshwaterStationSerializer,
        responses={
            201: FreshwaterStationSerializer(),
            400: openapi.Response("Bad Request - Invalid data provided for the freshwater station."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve Freshwater Station",
        operation_description="Retrieves a specific freshwater station instance by its ID.",
        responses={
            200: FreshwaterStationSerializer(),
            404: openapi.Response("Not Found - Freshwater station with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update Freshwater Station",
        operation_description="Updates an existing freshwater station instance fully.",
        request_body=FreshwaterStationSerializer,
        responses={
            200: FreshwaterStationSerializer(),
            400: openapi.Response("Bad Request - Invalid data provided."),
            404: openapi.Response("Not Found - Freshwater station with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Partially Update Freshwater Station",
        operation_description="Partially updates an existing freshwater station instance. Only include fields to be updated.",
        request_body=FreshwaterStationSerializer,
        responses={
            200: FreshwaterStationSerializer(),
            400: openapi.Response("Bad Request - Invalid data provided."),
            404: openapi.Response("Not Found - Freshwater station with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete Freshwater Station",
        operation_description="Deletes a specific freshwater station instance by its ID.",
        responses={
            204: openapi.Response("No Content - Freshwater station deleted successfully."),
            404: openapi.Response("Not Found - Freshwater station with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
