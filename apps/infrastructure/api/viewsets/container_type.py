"""
ContainerType viewset for the infrastructure app.

This module defines the viewset for the ContainerType model.
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

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

    @swagger_auto_schema(
        operation_summary="List Container Types",
        operation_description="Retrieves a list of all container types, with support for filtering, searching, and ordering.",
        responses={
            200: ContainerTypeSerializer(many=True),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create Container Type",
        operation_description="Creates a new container type.",
        request_body=ContainerTypeSerializer,
        responses={
            201: ContainerTypeSerializer(),
            400: openapi.Response("Bad Request - Invalid data provided for the container type."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve Container Type",
        operation_description="Retrieves a specific container type instance by its ID.",
        responses={
            200: ContainerTypeSerializer(),
            404: openapi.Response("Not Found - Container type with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update Container Type",
        operation_description="Updates an existing container type instance fully.",
        request_body=ContainerTypeSerializer,
        responses={
            200: ContainerTypeSerializer(),
            400: openapi.Response("Bad Request - Invalid data provided."),
            404: openapi.Response("Not Found - Container type with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Partially Update Container Type",
        operation_description="Partially updates an existing container type instance. Only include fields to be updated.",
        request_body=ContainerTypeSerializer,
        responses={
            200: ContainerTypeSerializer(),
            400: openapi.Response("Bad Request - Invalid data provided."),
            404: openapi.Response("Not Found - Container type with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete Container Type",
        operation_description="Deletes a specific container type instance by its ID.",
        responses={
            204: openapi.Response("No Content - Container type deleted successfully."),
            404: openapi.Response("Not Found - Container type with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
