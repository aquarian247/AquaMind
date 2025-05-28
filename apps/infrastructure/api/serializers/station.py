"""
FreshwaterStation serializer for the infrastructure app.

This module defines the serializer for the FreshwaterStation model.
"""

from rest_framework import serializers

from apps.infrastructure.models.station import FreshwaterStation
from apps.infrastructure.api.serializers.base import (
    TimestampedModelSerializer,
    NamedModelSerializer,
    LocationModelSerializer
)


class FreshwaterStationSerializer(TimestampedModelSerializer, NamedModelSerializer, LocationModelSerializer):
    """Serializer for the FreshwaterStation model."""
    
    geography_name = serializers.StringRelatedField(source='geography', read_only=True)
    station_type_display = serializers.CharField(source='get_station_type_display', read_only=True)

    class Meta:
        model = FreshwaterStation
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
