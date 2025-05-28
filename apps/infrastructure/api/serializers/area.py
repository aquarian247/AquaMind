"""
Area serializer for the infrastructure app.

This module defines the serializer for the Area model.
"""

from rest_framework import serializers

from apps.infrastructure.models.area import Area
from apps.infrastructure.api.serializers.geography import GeographySerializer
from apps.infrastructure.api.serializers.base import (
    TimestampedModelSerializer,
    NamedModelSerializer,
    LocationModelSerializer
)


class AreaSerializer(TimestampedModelSerializer, NamedModelSerializer,
                     LocationModelSerializer):
    """Serializer for the Area model."""

    geography_details = GeographySerializer(
        source='geography',
        read_only=True
    )

    class Meta:
        """Meta configuration for AreaSerializer."""
        model = Area
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, data):
        """Validate the latitude and longitude values."""
        if 'latitude' in data:
            if data['latitude'] < -90 or data['latitude'] > 90:
                raise serializers.ValidationError({
                    "latitude": "Latitude must be between -90 and 90."
                })

        if 'longitude' in data:
            if data['longitude'] < -180 or data['longitude'] > 180:
                raise serializers.ValidationError({
                    "longitude": "Longitude must be between -180 and 180."
                })

        return data
