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


class HallSummarySerializer(serializers.Serializer):
    """
    Serializer for hall KPI summary metrics.

    Returns aggregated metrics for a specific hall including
    container counts and active biomass/population data.
    """
    container_count = serializers.IntegerField(
        min_value=0,
        help_text="Number of containers in this hall."
    )
    active_biomass_kg = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        help_text="Sum of biomass_kg from active BatchContainerAssignments in containers within this hall."
    )
    population_count = serializers.IntegerField(
        min_value=0,
        help_text="Sum of population_count from active BatchContainerAssignments in containers within this hall."
    )
    avg_weight_kg = serializers.FloatField(
        min_value=0,
        help_text="Average weight in kg per fish (active_biomass_kg / population_count). Returns 0 if population_count is 0."
    )

    class Meta:
        fields = ['container_count', 'active_biomass_kg', 'population_count', 'avg_weight_kg']


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
