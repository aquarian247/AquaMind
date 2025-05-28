"""
Sensor serializer for the infrastructure app.

This module defines the serializer for the Sensor model.
"""

from rest_framework import serializers

from apps.infrastructure.models.sensor import Sensor
from apps.infrastructure.api.serializers.base import TimestampedModelSerializer, NamedModelSerializer


class SensorSerializer(TimestampedModelSerializer, NamedModelSerializer):
    """Serializer for the Sensor model."""
    
    container_name = serializers.StringRelatedField(source='container', read_only=True)
    sensor_type_display = serializers.CharField(source='get_sensor_type_display', read_only=True)

    class Meta:
        model = Sensor
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
