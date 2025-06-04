"""
Container serializer for the infrastructure app.

This module defines the serializer for the Container model.
"""

from rest_framework import serializers
from decimal import Decimal # Added for MinValueValidator
from django.core.validators import MinValueValidator

# Added for PrimaryKeyRelatedField querysets and type hints
from apps.infrastructure.models.container import Container
from apps.infrastructure.models.container_type import ContainerType
from apps.infrastructure.models.hall import Hall
from apps.infrastructure.models.area import Area
from apps.infrastructure.api.serializers.base import (
    TimestampedModelSerializer,
    NamedModelSerializer,
    ExclusiveLocationModelSerializer
)
# Removed: from apps.infrastructure.validation import validate_container_volume
# Validation logic is in the serializer's validate method and model's clean method.


class ContainerSerializer(TimestampedModelSerializer, NamedModelSerializer, ExclusiveLocationModelSerializer):
    """Serializer for the Container model."""

    name = serializers.CharField(
        max_length=100,
        help_text="Unique name for the container (e.g., Tank A1, Pen 3)."
    )
    container_type = serializers.PrimaryKeyRelatedField(
        queryset=ContainerType.objects.all(),
        help_text="ID of the container type (e.g., tank, pen, tray)."
    )
    container_type_name = serializers.StringRelatedField(
        source='container_type',
        read_only=True,
        help_text="Name of the container type."
    )
    hall = serializers.PrimaryKeyRelatedField(
        queryset=Hall.objects.all(),
        allow_null=True,
        required=False, # Made not required as it's one of hall/area
        help_text="ID of the hall this container is located in (if applicable). Mutually exclusive with 'area'."
    )
    hall_name = serializers.StringRelatedField(
        source='hall',
        read_only=True,
        allow_null=True,
        help_text="Name of the hall this container is located in."
    )
    area = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all(),
        allow_null=True,
        required=False, # Made not required as it's one of hall/area
        help_text="ID of the sea area this container is located in (if applicable). Mutually exclusive with 'hall'."
    )
    area_name = serializers.StringRelatedField(
        source='area',
        read_only=True,
        allow_null=True,
        help_text="Name of the sea area this container is located in."
    )
    volume_m3 = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))], # Assuming volume must be positive
        help_text="Volume of the container in cubic meters (e.g., 150.75)."
    )
    max_biomass_kg = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Maximum recommended biomass capacity for this container in kilograms (e.g., 5000.00)."
    )
    feed_recommendations_enabled = serializers.BooleanField(
        default=True,
        help_text="Indicates if automatic feed recommendations are enabled for this container."
    )
    active = serializers.BooleanField(
        default=True,
        help_text="Indicates if the container is currently active and in use."
    )

    class Meta:
        model = Container
        fields = [
            'id', 'name', 'container_type', 'container_type_name',
            'hall', 'hall_name', 'area', 'area_name',
            'volume_m3', 'max_biomass_kg', 'feed_recommendations_enabled', 'active',
            'created_at', 'updated_at'
        ]
        read_only_fields = (
            'id', 'created_at', 'updated_at',
            'container_type_name', 'hall_name', 'area_name'
        )

    def validate(self, data):
        """
        Validate the container data.

        Validates that:
        1. The container is in either a hall or area, not both (handled by parent class ExclusiveLocationModelSerializer).
        2. The volume doesn't exceed container type's maximum volume.

        Args:
            data: The serializer data

        Returns:
            dict: The validated data
        """
        # Parent class (ExclusiveLocationModelSerializer) validation for hall/area exclusivity
        data = super().validate(data)

        # Validate volume against container type max volume
        # If container_type is being updated, data['container_type'] will be a ContainerType instance.
        # If not updated and it's a partial update, self.instance.container_type should be used.
        container_type_instance = data.get('container_type')
        if not container_type_instance and self.instance: # Handle partial updates where container_type isn't changing
            container_type_instance = self.instance.container_type

        volume = data.get('volume_m3')
        if not volume and self.instance: # Handle partial updates where volume_m3 isn't changing
             volume = self.instance.volume_m3


        if container_type_instance and volume:
            if volume > container_type_instance.max_volume_m3:
                raise serializers.ValidationError({
                    "volume_m3": f"Volume ({volume} m³) cannot exceed container type "
                                 f"'{container_type_instance.name}' maximum volume of {container_type_instance.max_volume_m3} m³."
                })

        return data
