"""
Geography viewset for the infrastructure app.

This module defines the viewset for the Geography model.
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

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

    @swagger_auto_schema(
        operation_summary="List Geographies",
        operation_description="Retrieves a list of all geographical locations/zones, with support for filtering, searching, and ordering.",
        responses={
            200: GeographySerializer(many=True),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create Geography",
        operation_description="Creates a new geographical location or zone.",
        request_body=GeographySerializer,
        responses={
            201: GeographySerializer(),
            400: openapi.Response("Bad Request - Invalid data provided for the geography."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve Geography",
        operation_description="Retrieves a specific geography instance by its ID.",
        responses={
            200: GeographySerializer(),
            404: openapi.Response("Not Found - Geography with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update Geography",
        operation_description="Updates an existing geography instance fully.",
        request_body=GeographySerializer,
        responses={
            200: GeographySerializer(),
            400: openapi.Response("Bad Request - Invalid data provided."),
            404: openapi.Response("Not Found - Geography with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Partially Update Geography",
        operation_description="Partially updates an existing geography instance. Only include fields to be updated.",
        request_body=GeographySerializer,
        responses={
            200: GeographySerializer(),
            400: openapi.Response("Bad Request - Invalid data provided."),
            404: openapi.Response("Not Found - Geography with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete Geography",
        operation_description="Deletes a specific geography instance by its ID.",
        responses={
            204: openapi.Response("No Content - Geography deleted successfully."),
            404: openapi.Response("Not Found - Geography with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
