"""
FeedContainer serializer for the infrastructure app.

This module defines the serializer for the FeedContainer model.
"""

from rest_framework import serializers
from decimal import Decimal # Added for MinValueValidator
from django.core.validators import MinValueValidator

from apps.infrastructure.models.feed_container import FeedContainer
# Added for PrimaryKeyRelatedField querysets
from apps.infrastructure.models.hall import Hall
from apps.infrastructure.models.area import Area
from apps.infrastructure.api.serializers.base import (
    TimestampedModelSerializer,
    NamedModelSerializer,
    ExclusiveLocationModelSerializer
)


class FeedContainerSerializer(TimestampedModelSerializer, NamedModelSerializer, ExclusiveLocationModelSerializer):
    """Serializer for the FeedContainer model."""

    name = serializers.CharField(
        max_length=100,
        help_text="Unique name for the feed container (e.g., 'Silo 1', 'Feed Barge Alpha')."
    )
    container_type = serializers.ChoiceField(
        choices=FeedContainer.CONTAINER_TYPES,
        help_text="Type of the feed container (e.g., SILO, BARGE, TANK)."
    )
    container_type_display = serializers.CharField(
        source='get_container_type_display',
        read_only=True,
        help_text="Human-readable display name for the container type."
    )
    hall = serializers.PrimaryKeyRelatedField(
        queryset=Hall.objects.all(),
        allow_null=True,
        required=False,
        help_text="ID of the hall this feed container is associated with (if applicable). Mutually exclusive with 'area'."
    )
    hall_name = serializers.StringRelatedField(
        source='hall',
        read_only=True,
        allow_null=True,
        help_text="Name of the hall this feed container is associated with."
    )
    area = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all(),
        allow_null=True,
        required=False,
        help_text="ID of the sea area this feed container is associated with (if applicable). Mutually exclusive with 'hall'."
    )
    area_name = serializers.StringRelatedField(
        source='area',
        read_only=True,
        allow_null=True,
        help_text="Name of the sea area this feed container is associated with."
    )
    capacity_kg = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))], # Assuming capacity must be positive
        help_text="Total capacity of the feed container in kilograms (e.g., 50000.00)."
    )
    # current_level_kg might be a dynamic field, handled elsewhere or added if it becomes a model field.
    active = serializers.BooleanField(
        default=True,
        help_text="Indicates if the feed container is currently active and in use."
    )

    class Meta:
        model = FeedContainer
        fields = [
            'id', 'name', 'container_type', 'container_type_display',
            'hall', 'hall_name', 'area', 'area_name',
            'capacity_kg', 'active',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'container_type_display', 'hall_name', 'area_name'
        ]
        # Note: The ExclusiveLocationModelSerializer handles the validation for hall/area exclusivity.
