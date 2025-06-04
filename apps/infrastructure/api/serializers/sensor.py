"""
Sensor serializer for the infrastructure app.

This module defines the serializer for the Sensor model.
"""

from rest_framework import serializers

from apps.infrastructure.models.sensor import Sensor
from apps.infrastructure.models.container import Container # Added for PrimaryKeyRelatedField
from apps.infrastructure.api.serializers.base import TimestampedModelSerializer, NamedModelSerializer


class SensorSerializer(TimestampedModelSerializer, NamedModelSerializer):
    """Serializer for the Sensor model."""

    name = serializers.CharField(
        max_length=100,
        help_text="User-defined name for the sensor (e.g., 'Tank 1 Temp Sensor', 'Oxygen Probe - Pen 5')."
    )
    sensor_type = serializers.ChoiceField(
        choices=Sensor.SENSOR_TYPES,
        help_text="Type of the sensor (e.g., TEMPERATURE, OXYGEN, PH)."
    )
    sensor_type_display = serializers.CharField(
        source='get_sensor_type_display',
        read_only=True,
        help_text="Human-readable display name for the sensor type."
    )
    container = serializers.PrimaryKeyRelatedField(
        queryset=Container.objects.all(),
        help_text="ID of the container where this sensor is installed."
    )
    container_name = serializers.StringRelatedField(
        source='container',
        read_only=True,
        help_text="Name of the container where this sensor is installed."
    )
    serial_number = serializers.CharField(
        max_length=100,
        allow_blank=True,
        required=False,
        help_text="Manufacturer's serial number for the sensor. Optional."
    )
    manufacturer = serializers.CharField(
        max_length=100,
        allow_blank=True,
        required=False,
        help_text="Manufacturer of the sensor. Optional."
    )
    installation_date = serializers.DateField(
        allow_null=True,
        required=False,
        help_text="Date when the sensor was installed. Optional. Format: YYYY-MM-DD."
    )
    last_calibration_date = serializers.DateField(
        allow_null=True,
        required=False,
        help_text="Date when the sensor was last calibrated. Optional. Format: YYYY-MM-DD."
    )
    active = serializers.BooleanField(
        default=True,
        help_text="Indicates if the sensor is currently active and providing readings."
    )

    class Meta:
        model = Sensor
        fields = [
            'id', 'name', 'sensor_type', 'sensor_type_display',
            'container', 'container_name',
            'serial_number', 'manufacturer', 'installation_date', 'last_calibration_date',
            'active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'sensor_type_display', 'container_name'
        ]
