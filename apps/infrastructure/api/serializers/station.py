"""
FreshwaterStation serializer for the infrastructure app.

This module defines the serializer for the FreshwaterStation model.
"""

from rest_framework import serializers
from django.core.validators import MinValueValidator, MaxValueValidator # Added for lat/lon validators

from apps.infrastructure.models.station import FreshwaterStation
from apps.infrastructure.models.geography import Geography # Added for PrimaryKeyRelatedField
from apps.infrastructure.api.serializers.base import (
    TimestampedModelSerializer,
    NamedModelSerializer,
    LocationModelSerializer
)


class FreshwaterStationSerializer(TimestampedModelSerializer, NamedModelSerializer, LocationModelSerializer):
    """Serializer for the FreshwaterStation model."""

    name = serializers.CharField(
        max_length=100,
        help_text="Unique name for the freshwater station (e.g., 'Main Hatchery', 'Broodstock Unit Alpha')."
    )
    station_type = serializers.ChoiceField(
        choices=FreshwaterStation.STATION_TYPES,
        help_text="Type of the station (e.g., FRESHWATER, BROODSTOCK)."
    )
    station_type_display = serializers.CharField(
        source='get_station_type_display',
        read_only=True,
        help_text="Human-readable display name for the station type."
    )
    geography = serializers.PrimaryKeyRelatedField(
        queryset=Geography.objects.all(),
        help_text="ID of the geographical region this station belongs to."
    )
    geography_name = serializers.StringRelatedField(
        source='geography',
        read_only=True,
        help_text="Name of the geographical region this station belongs to."
    )
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        help_text="Latitude of the station (e.g., 62.000000). Usually set via map interface."
    )
    longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        help_text="Longitude of the station (e.g., -6.783333). Usually set via map interface."
    )
    description = serializers.CharField(
        allow_blank=True,
        required=False,
        style={'base_template': 'textarea.html'},
        help_text="Optional description of the freshwater station, its facilities, or purpose."
    )
    active = serializers.BooleanField(
        default=True,
        help_text="Indicates if the freshwater station is currently active and operational."
    )

    class Meta:
        model = FreshwaterStation
        fields = [
            'id', 'name', 'station_type', 'station_type_display',
            'geography', 'geography_name',
            'latitude', 'longitude', 'description', 'active',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'station_type_display', 'geography_name'
        ]
