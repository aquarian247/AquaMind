"""
Hall viewset for the infrastructure app.

This module defines the viewset for the Hall model.
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

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

    @swagger_auto_schema(
        operation_summary="List Halls",
        operation_description="Retrieves a list of all halls within the facility, with support for filtering, searching, and ordering.",
        responses={
            200: HallSerializer(many=True),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create Hall",
        operation_description="Creates a new hall within the facility.",
        request_body=HallSerializer,
        responses={
            201: HallSerializer(),
            400: openapi.Response("Bad Request - Invalid data provided for the hall."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve Hall",
        operation_description="Retrieves a specific hall instance by its ID.",
        responses={
            200: HallSerializer(),
            404: openapi.Response("Not Found - Hall with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update Hall",
        operation_description="Updates an existing hall instance fully.",
        request_body=HallSerializer,
        responses={
            200: HallSerializer(),
            400: openapi.Response("Bad Request - Invalid data provided."),
            404: openapi.Response("Not Found - Hall with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Partially Update Hall",
        operation_description="Partially updates an existing hall instance. Only include fields to be updated.",
        request_body=HallSerializer,
        responses={
            200: HallSerializer(),
            400: openapi.Response("Bad Request - Invalid data provided."),
            404: openapi.Response("Not Found - Hall with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete Hall",
        operation_description="Deletes a specific hall instance by its ID.",
        responses={
            204: openapi.Response("No Content - Hall deleted successfully."),
            404: openapi.Response("Not Found - Hall with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
