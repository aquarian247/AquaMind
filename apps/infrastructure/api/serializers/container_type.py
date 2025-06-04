"""
ContainerType serializer for the infrastructure app.

This module defines the serializer for the ContainerType model.
"""

from rest_framework import serializers
from decimal import Decimal # Added for MinValueValidator
from django.core.validators import MinValueValidator

from apps.infrastructure.models.container_type import ContainerType
from apps.infrastructure.api.serializers.base import TimestampedModelSerializer, NamedModelSerializer


class ContainerTypeSerializer(TimestampedModelSerializer, NamedModelSerializer):
    """Serializer for the ContainerType model."""

    name = serializers.CharField(
        max_length=100,
        help_text="Unique name for the container type (e.g., 'Circular Tank 10m', 'Square Pen 20x20')."
    )
    category = serializers.ChoiceField(
        choices=ContainerType.CONTAINER_CATEGORIES,
        help_text="Category of the container type (e.g., TANK, PEN, TRAY)."
    )
    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True,
        help_text="Human-readable display name for the category."
    )
    max_volume_m3 = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))], # Assuming volume must be positive
        help_text="Maximum design volume of this container type in cubic meters (e.g., 100.50)."
    )
    description = serializers.CharField(
        allow_blank=True,
        required=False,
        style={'base_template': 'textarea.html'}, # Suggests a larger input field in UI
        help_text="Optional description of the container type, its characteristics, or usage notes."
    )

    class Meta:
        model = ContainerType
        fields = [
            'id', 'name', 'category', 'category_display',
            'max_volume_m3', 'description',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'category_display']
