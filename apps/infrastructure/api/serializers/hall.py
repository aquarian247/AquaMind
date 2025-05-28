"""
Hall serializer for the infrastructure app.

This module defines the serializer for the Hall model.
"""

from rest_framework import serializers

from apps.infrastructure.models.hall import Hall
from apps.infrastructure.api.serializers.base import TimestampedModelSerializer, NamedModelSerializer


class HallSerializer(TimestampedModelSerializer, NamedModelSerializer):
    """Serializer for the Hall model."""
    
    freshwater_station_name = serializers.StringRelatedField(
        source='freshwater_station', read_only=True
    )

    class Meta:
        model = Hall
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
