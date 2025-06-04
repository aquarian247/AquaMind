"""
Area viewset for the infrastructure app.

This module defines the viewset for the Area model.
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.infrastructure.models.area import Area
from apps.infrastructure.api.serializers.area import AreaSerializer


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
    
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'geography', 'active']
    search_fields = ['name', 'geography__name']
    ordering_fields = ['name', 'geography__name', 'created_at']
    ordering = ['name']

    @swagger_auto_schema(
        operation_summary="List Areas",
        operation_description="Retrieves a list of all areas, with support for filtering, searching, and ordering.",
        responses={
            200: AreaSerializer(many=True),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create Area",
        operation_description="Creates a new area within a specified geography.",
        request_body=AreaSerializer,
        responses={
            201: AreaSerializer(),
            400: openapi.Response("Bad Request - Invalid data provided for the area."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve Area",
        operation_description="Retrieves a specific area instance by its ID.",
        responses={
            200: AreaSerializer(),
            404: openapi.Response("Not Found - Area with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update Area",
        operation_description="Updates an existing area instance fully.",
        request_body=AreaSerializer,
        responses={
            200: AreaSerializer(),
            400: openapi.Response("Bad Request - Invalid data provided."),
            404: openapi.Response("Not Found - Area with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Partially Update Area",
        operation_description="Partially updates an existing area instance. Only include fields to be updated.",
        request_body=AreaSerializer,
        responses={
            200: AreaSerializer(),
            400: openapi.Response("Bad Request - Invalid data provided."),
            404: openapi.Response("Not Found - Area with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete Area",
        operation_description="Deletes a specific area instance by its ID.",
        responses={
            204: openapi.Response("No Content - Area deleted successfully."),
            404: openapi.Response("Not Found - Area with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
