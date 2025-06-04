"""
Area serializer for the infrastructure app.

This module defines the serializer for the Area model.
"""

from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from rest_framework import serializers

from apps.infrastructure.models.area import Area
from apps.infrastructure.models.geography import Geography # Added for PrimaryKeyRelatedField queryset
from apps.infrastructure.api.serializers.geography import GeographySerializer
from apps.infrastructure.api.serializers.base import (
    TimestampedModelSerializer,
    NamedModelSerializer,
    LocationModelSerializer
)


class AreaSerializer(TimestampedModelSerializer, NamedModelSerializer,
                     LocationModelSerializer):
    """Serializer for the Area model."""

    name = serializers.CharField(
        max_length=100,
        help_text="Unique name for the sea area."
    )
    geography = serializers.PrimaryKeyRelatedField(
        queryset=Geography.objects.all(),
        help_text="ID of the geographical zone this area belongs to."
    )
    geography_details = GeographySerializer(
        source='geography',
        read_only=True,
        help_text="Detailed information about the associated geographical zone."
    )
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        min_value=Decimal('-90.0'),
        max_value=Decimal('90.0'),
        validators=[MinValueValidator(Decimal('-90.0')), MaxValueValidator(Decimal('90.0'))],
        help_text="Latitude of the area's central point (e.g., 60.123456). Must be between -90 and 90."
    )
    longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        min_value=Decimal('-180.0'),
        max_value=Decimal('180.0'),
        validators=[MinValueValidator(Decimal('-180.0')), MaxValueValidator(Decimal('180.0'))],
        help_text="Longitude of the area's central point (e.g., 5.123456). Must be between -180 and 180."
    )
    max_biomass = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))], # Assuming max_biomass cannot be negative
        help_text="Maximum permissible biomass capacity for this area, in kilograms (e.g., 100000.00)."
    )
    active = serializers.BooleanField(
        default=True,
        help_text="Indicates if the area is currently active and available for use."
    )

    class Meta:
        """Meta configuration for AreaSerializer."""
        model = Area
        fields = [
            'id', 'name', 'geography', 'geography_details', 'latitude',
            'longitude', 'max_biomass', 'active',
            'created_at', 'updated_at'
        ] # Explicitly list fields
        read_only_fields = ['id', 'created_at', 'updated_at', 'geography_details']

    def validate(self, data):
        """Validate the latitude and longitude values."""
        # Validation for latitude and longitude is handled by field validators
        # and LocationModelSerializer if its validation methods are called.
        # Keeping custom validation if specific combined logic is needed or
        # if LocationModelSerializer's validation isn't automatically triggered.

        # If LocationModelSerializer's validate_latitude/longitude are not used,
        # uncomment and adapt the following:
        # latitude = data.get('latitude', getattr(self.instance, 'latitude', None))
        # longitude = data.get('longitude', getattr(self.instance, 'longitude', None))

        # if latitude is not None and (latitude < -90 or latitude > 90):
        #     raise serializers.ValidationError({
        #         "latitude": "Latitude must be between -90 and 90."
        #     })

        # if longitude is not None and (longitude < -180 or longitude > 180):
        #     raise serializers.ValidationError({
        #         "longitude": "Longitude must be between -180 and 180."
        #     })
        return super().validate(data) # Ensure base class validations are called if any
