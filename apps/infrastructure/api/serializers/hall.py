"""
Hall serializer for the infrastructure app.

This module defines the serializer for the Hall model.
"""

from rest_framework import serializers
from decimal import Decimal
from django.core.validators import MinValueValidator

from apps.infrastructure.models.hall import Hall
from apps.infrastructure.models.station import FreshwaterStation
from apps.infrastructure.api.serializers.base import TimestampedModelSerializer, NamedModelSerializer


class HallSerializer(TimestampedModelSerializer, NamedModelSerializer):
    """Serializer for the Hall model."""

    name = serializers.CharField(
        max_length=100,
        help_text="Unique name for the hall within its station (e.g., 'Hatchery Hall A', 'Grow-out Section 1')."
    )
    freshwater_station = serializers.PrimaryKeyRelatedField(
        queryset=FreshwaterStation.objects.all(),
        help_text="ID of the freshwater station this hall belongs to."
    )
    freshwater_station_name = serializers.StringRelatedField(
        source='freshwater_station',
        read_only=True,
        help_text="Name of the freshwater station this hall belongs to."
    )
    description = serializers.CharField(
        allow_blank=True,
        required=False,
        style={'base_template': 'textarea.html'},
        help_text="Optional description of the hall, its purpose, or specific characteristics."
    )
    area_sqm = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        allow_null=True,
        required=False,
        validators=[MinValueValidator(Decimal('0.01'))], # Assuming area must be positive if provided
        help_text="Surface area of the hall in square meters (e.g., 500.75). Optional."
    )
    active = serializers.BooleanField(
        default=True,
        help_text="Indicates if the hall is currently active and in use."
    )

    class Meta:
        model = Hall
        fields = [
            'id', 'name', 'freshwater_station', 'freshwater_station_name',
            'description', 'area_sqm', 'active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'freshwater_station_name']
