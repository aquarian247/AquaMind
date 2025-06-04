"""
Sensor viewset for the infrastructure app.

This module defines the viewset for the Sensor model.
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.infrastructure.models.sensor import Sensor
from apps.infrastructure.api.serializers.sensor import SensorSerializer


class SensorViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Sensors within the aquaculture facility.

    Sensors are devices used to monitor various environmental parameters (e.g., temperature,
    pH, dissolved oxygen) within specific containers. Each sensor can be of a particular
    type, have a unique serial number, and be associated with a manufacturer.
    This endpoint allows for full CRUD operations on Sensor instances.

    **Filtering:**
    - `name`: Filter by the exact name of the sensor.
    - `sensor_type`: Filter by the type of the sensor (e.g., TEMPERATURE, PH, DO).
    - `container`: Filter by the ID of the Container where the sensor is installed.
    - `active`: Filter by active status (boolean).

    **Searching:**
    - `name`: Search by sensor name (partial matches).
    - `serial_number`: Search by the sensor's serial number.
    - `manufacturer`: Search by the sensor's manufacturer.
    - `container__name`: Search by the name of the Container where the sensor is installed.

    **Ordering:**
    - `name` (default)
    - `sensor_type`
    - `container__name`: Order by the name of the associated Container.
    - `created_at`
    """
    
    queryset = Sensor.objects.all()
    serializer_class = SensorSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'sensor_type', 'container', 'active']
    search_fields = ['name', 'serial_number', 'manufacturer', 'container__name']
    ordering_fields = ['name', 'sensor_type', 'container__name', 'created_at']
    ordering = ['name']

    @swagger_auto_schema(
        operation_summary="List Sensors",
        operation_description="Retrieves a list of all sensors, with support for filtering, searching, and ordering.",
        responses={
            200: SensorSerializer(many=True),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create Sensor",
        operation_description="Creates a new sensor and associates it with a container.",
        request_body=SensorSerializer,
        responses={
            201: SensorSerializer(),
            400: openapi.Response("Bad Request - Invalid data provided for the sensor."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve Sensor",
        operation_description="Retrieves a specific sensor instance by its ID.",
        responses={
            200: SensorSerializer(),
            404: openapi.Response("Not Found - Sensor with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Update Sensor",
        operation_description="Updates an existing sensor instance fully.",
        request_body=SensorSerializer,
        responses={
            200: SensorSerializer(),
            400: openapi.Response("Bad Request - Invalid data provided."),
            404: openapi.Response("Not Found - Sensor with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Partially Update Sensor",
        operation_description="Partially updates an existing sensor instance. Only include fields to be updated.",
        request_body=SensorSerializer,
        responses={
            200: SensorSerializer(),
            400: openapi.Response("Bad Request - Invalid data provided."),
            404: openapi.Response("Not Found - Sensor with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Delete Sensor",
        operation_description="Deletes a specific sensor instance by its ID.",
        responses={
            204: openapi.Response("No Content - Sensor deleted successfully."),
            404: openapi.Response("Not Found - Sensor with the specified ID does not exist."),
            401: openapi.Response("Unauthorized - Authentication credentials were not provided or were invalid."),
            403: openapi.Response("Forbidden - You do not have permission to perform this action.")
        }
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
