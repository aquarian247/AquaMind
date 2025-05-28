"""
FeedContainer serializer for the infrastructure app.

This module defines the serializer for the FeedContainer model.
"""

from rest_framework import serializers

from apps.infrastructure.models.feed_container import FeedContainer
from apps.infrastructure.api.serializers.base import (
    TimestampedModelSerializer,
    NamedModelSerializer,
    ExclusiveLocationModelSerializer
)


class FeedContainerSerializer(TimestampedModelSerializer, NamedModelSerializer, ExclusiveLocationModelSerializer):
    """Serializer for the FeedContainer model."""
    
    container_type_display = serializers.CharField(source='get_container_type_display', read_only=True)
    hall_name = serializers.StringRelatedField(source='hall', read_only=True)
    area_name = serializers.StringRelatedField(source='area', read_only=True)

    class Meta:
        model = FeedContainer
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
