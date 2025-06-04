"""
FeedContainer viewset for the infrastructure app.

This module defines the viewset for the FeedContainer model.
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.infrastructure.models.feed_container import FeedContainer
from apps.infrastructure.api.serializers.feed_container import FeedContainerSerializer


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
    - `hall`: Filter by the ID of the parent Hall where the feed container is located.
    - `area`: Filter by the ID of the parent Area where the feed container is located.
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
    filterset_fields = ['name', 'container_type', 'hall', 'area', 'active']
    search_fields = ['name', 'hall__name', 'area__name']
    ordering_fields = ['name', 'container_type', 'created_at']
    ordering = ['name']

    @swagger_auto_schema(
        operation_summary="List Feed Containers",
        operation_description="Retrieves a list of all feed containers, with support for filtering, searching, and ordering.",
        responses={
            200: FeedContainerSerializer(many=True),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create Feed Container",
        operation_description="Creates a new feed container within the facility.",
        request_body=FeedContainerSerializer,
        responses={
            201: FeedContainerSerializer(),
            400: openapi.Response("Bad Request - Invalid data provided for the feed container."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve Feed Container",
        operation_description="Retrieves a specific feed container instance by its ID.",
        responses={
            200: FeedContainerSerializer(),
            404: openapi.Response("Not Found - Feed container with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update Feed Container",
        operation_description="Updates an existing feed container instance fully.",
        request_body=FeedContainerSerializer,
        responses={
            200: FeedContainerSerializer(),
            400: openapi.Response("Bad Request - Invalid data provided."),
            404: openapi.Response("Not Found - Feed container with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Partially Update Feed Container",
        operation_description="Partially updates an existing feed container instance. Only include fields to be updated.",
        request_body=FeedContainerSerializer,
        responses={
            200: FeedContainerSerializer(),
            400: openapi.Response("Bad Request - Invalid data provided."),
            404: openapi.Response("Not Found - Feed container with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete Feed Container",
        operation_description="Deletes a specific feed container instance by its ID.",
        responses={
            204: openapi.Response("No Content - Feed container deleted successfully."),
            404: openapi.Response("Not Found - Feed container with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
