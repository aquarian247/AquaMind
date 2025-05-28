"""
ContainerType serializer for the infrastructure app.

This module defines the serializer for the ContainerType model.
"""

from rest_framework import serializers

from apps.infrastructure.models.container_type import ContainerType
from apps.infrastructure.api.serializers.base import TimestampedModelSerializer, NamedModelSerializer


class ContainerTypeSerializer(TimestampedModelSerializer, NamedModelSerializer):
    """Serializer for the ContainerType model."""
    
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = ContainerType
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
