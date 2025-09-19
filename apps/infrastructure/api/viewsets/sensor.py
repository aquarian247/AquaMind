"""
Sensor viewset for the infrastructure app.

This module defines the viewset for the Sensor model.
"""

from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import FilterSet

from apps.infrastructure.models.sensor import Sensor
from apps.infrastructure.api.serializers.sensor import SensorSerializer


class SensorFilter(FilterSet):
    """Custom filterset for Sensor model to support __in lookups."""

    class Meta:
        model = Sensor
        fields = {
            'name': ['exact', 'icontains'],
            'sensor_type': ['exact'],
            'container': ['exact', 'in'],
            'active': ['exact']
        }

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
    - `container__in`: Filter by multiple Container IDs (comma-separated).
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
    filterset_class = SensorFilter
    search_fields = ['name', 'serial_number', 'manufacturer', 'container__name']
    ordering_fields = ['name', 'sensor_type', 'container__name', 'created_at']
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
