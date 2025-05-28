"""
Container serializer for the infrastructure app.

This module defines the serializer for the Container model.
"""

from rest_framework import serializers

from apps.infrastructure.models.container import Container
from apps.infrastructure.api.serializers.base import (
    TimestampedModelSerializer,
    NamedModelSerializer,
    ExclusiveLocationModelSerializer
)
from apps.infrastructure.validation import validate_container_volume


class ContainerSerializer(TimestampedModelSerializer, NamedModelSerializer, ExclusiveLocationModelSerializer):
    """Serializer for the Container model."""
    
    container_type_name = serializers.StringRelatedField(source='container_type', read_only=True)
    hall_name = serializers.StringRelatedField(source='hall', read_only=True)
    area_name = serializers.StringRelatedField(source='area', read_only=True)

    class Meta:
        model = Container
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def validate(self, data):
        """
        Validate the container data.

        Validates that:
        1. The container is in either a hall or area, not both (handled by parent class)
        2. The volume doesn't exceed container type max volume

        Args:
            data: The serializer data

        Returns:
            dict: The validated data
        """
        # First run the parent class validation (exclusive location)
        data = super().validate(data)
        
        # Validate volume against container type max volume
        container_type = data.get('container_type')
        volume = data.get('volume_m3')
        
        if container_type and volume and volume > container_type.max_volume_m3:
            raise serializers.ValidationError({
                "volume_m3": f"Volume cannot exceed container type maximum volume of {container_type.max_volume_m3} m³."
            })
        
        return data
